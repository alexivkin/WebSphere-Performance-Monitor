'''
Queries current running WAS stats and saves them to a file
(C) 2015 Alex Ivkin

Run using the following command:
wsadmin.[bat|sh] -lang jython -user wsadmin -password wsadmin -f collectWASPerformanceStats.py <stats_file> [-l]

You can omit -user and -password. wsadmin is in \Program Files\IBM\WebSphere\AppServer\bin\ on a default windows installation

NOTE: On Windows, due to WebSphere weirdness you have to use FORWARD slashes (/) in the output file name. Otherwise the backward slashes (\) need to be doubled or they will turn into escape sequences

Use -l after the output file name to export the list of all available performance MBeans to the output file and quit

'''
import re,sys,time,os,java

if len(sys.argv)==0:
    print __doc__
    sys.exit(1)

#perfObject = AdminControl.completeObjectName('type=Perf,*') #@UndefinedVariable - comes from WAS
perfHash={}
perfObjects=AdminControl.queryNames('type=Perf,*').split('\n') # could be one perfmbean per WAS instance
if perfObjects is None or not perfObjects:
    print "Can not retreive the performance MBean. Make sure PMI (performance metrics) is enabled on the server"
# convert to object names and hash under individual process names
for p in perfObjects:
    perfObjectName=AdminControl.makeObjectName(p) # javax.management.ObjectName. Get tog full string - p.getKeyPropertyListString()
    process=perfObjectName.getKeyProperty("process")
    if process is None:
        print "Performance object %s is not associated with a process." % p
    else:
        perfHash[process]=perfObjectName
print "Performance beans found: %s" % ",".join(perfHash.keys())
# Enable PMI data using the pre-defined statistic sets.
#AdminControl.invoke_jmx (perfObjName, 'setStatisticSet', ['all'], ['java.lang.String']) #@UnusedVariable @UndefinedVariable

if len(sys.argv) > 1 and sys.argv[1]=='-l':
    # list objects with stats
    f_out=open(sys.argv[0],"w")
    statName={}
    statDescription={}
    print "Listing objects ..."
    for a in AdminControl.queryNames('*').split('\n'): #type=ConnectionPool, @UndefinedVariable
         try:
             # queriying the first available perfmbean they all return the same set of performance metrics
             config=AdminControl.invoke_jmx(perfHash[perfHash.keys()[0]], 'getConfig', [AdminControl.makeObjectName(a)], ['javax.management.ObjectName'])  # returns PmiModuleConfig object
             if config is not None: # record the config specs, if we have not already seen it
                 statName[a]=config.getShortName()
                 statDescription[config.getShortName()]=[config.getDescription(), ",".join([d.name for d in config.listAllData()])]
         except:
             pass
    print "Writing stat descriptions..."
    skeys=statDescription.keys()
    skeys.sort()
    for s in skeys:
         print >> f_out, "%-25s-%s [%s]" % (s,statDescription[s][0],statDescription[s][1])
    print "Writing stat names..."
    print >> f_out, "\n\n"
    skeys=statName.keys()
    skeys.sort() # sort() does not return a list but does sorting in place, hence the ugly multi-liner
    for s in skeys:
         print >> f_out, "%-25s=%s" % (statName[s], s)
    print "done."
    sys.exit(0)

# load config
config={}
try:
    for line in open("performance.prop","r").readlines():
       line=line.strip()
       if not line.startswith("#") and "=" in line:
           config[line.split("=",1)[0].strip()]=line.split("=",1)[1].strip()
    print "Settings loaded: %s" % ",".join(config.keys())
except:
    print "performance.prop can't be loaded: %s" % sys.exc_info()[0]
    sys.exit(1)

# convert conf into wasobjects and create a header
WASobjects={}
#statsize={}         # track the number of individual statistics in each perf object. Useful for maintaining proper CSV line in case some stats need to be skipped
namelist=['Date','Time'] # list is used for ordering, hashtables are unordered
configkeys=config.keys()
configkeys.sort()
for c in configkeys:
    if c == "wait":     # skip the 'wait' config line, since it's not a watched stat
        continue
    try:
        WASobjects[c]=AdminControl.makeObjectName(AdminControl.completeObjectName(config[c]))
        # list all possible stats
        statconfig=AdminControl.invoke_jmx(perfHash[perfHash.keys()[0]], 'getConfig', [WASobjects[c]], ['javax.management.ObjectName'])
        if statconfig is None:
            print "Empty stat config for %s. Skipping..." % c
            continue
        #statsize[c]=0
        for d in statconfig.listAllData():
            #statsize[c]+=1
            namelist.append(c+" "+d.name)
    except:
        print "Problem looking up %s: %s, %s. Skipping..." % (c,sys.exc_info()[0],sys.exc_info()[1])

# Simulate CSV. csv library may not be available in WAS's outdated jython
header=",".join(namelist)
# open the output file
try:
    if os.path.isfile(sys.argv[0]) and open(sys.argv[0],"r").readline().strip() == header: # check if the existing header matches the new one
        print "Appending to the existing file..."
        f_out=open(sys.argv[0],"a")
    else:
        print "Starting a new stats collection file..."
        f_out=open(sys.argv[0],"w")
        print>>f_out,header
except:
    print "Error opening file %s\n%s" % (sys.argv[0],sys.exc_info()[1])
    sys.exit(2)

def get_value(s):
    value="."
    if str(s.getClass())=='com.ibm.ws.pmi.stat.BoundedRangeStatisticImpl': # bounded range
        value=s.current
    elif str(s.getClass())=='com.ibm.ws.pmi.stat.CountStatisticImpl': # count statistics
        value=s.count
    elif str(s.getClass())=='com.ibm.ws.pmi.stat.DoubleStatisticImpl':
        value=s.double
    elif str(s.getClass())=='com.ibm.ws.pmi.stat.TimeStatisticImpl':  # max, min, minTime,maxTime, totalTime, sumOfSquares, delta, mean
        value=s.count
    elif str(s.getClass())=='com.ibm.ws.pmi.stat.RangeStatisticImpl':   # lowWaterMark, highWaterMark, integral, delta, mean, current
        value=s.current
    elif str(s.getClass())=='com.ibm.ws.pmi.stat.AverageStatisticImpl': # max, mean,min,sumOfSquares,total
        value=s.count
    else:
        value=s.getClass() # .class works too
    return value

print "Pulling Websphere statistics...Press Ctrl-C to interrupt"

while 1:
    try:
        statshash={}
        for t in namelist:
            if t=="Date":
                statshash[t]=time.strftime("%m/%d/%Y", time.localtime())
            elif t=="Time":
                statshash[t]=time.strftime("%H:%M:%S", time.localtime())
            else:
                statshash[t]=""
        print "%s,%s..." % (statshash["Date"],statshash["Time"])
        for obj in WASobjects.keys():  # the sorting is not really required because the ordering in CSV is controlled by the ordering in namelist
            process=WASobjects[obj].getKeyProperty("process")
            if process is None:
                print "No process definition for %s. Skipping..." % obj
            elif process not in perfHash.keys():
                print "Metrics process %s for %s has no matching perfomance bean to pull from. Skipping..." % (process,obj)
            else:
                # pull actual statistics from the associated performance bean
                stats=AdminControl.invoke_jmx(perfHash[process], 'getStatsObject', [WASobjects[obj], java.lang.Boolean ('false')], ['javax.management.ObjectName', 'java.lang.Boolean']) # returns com.ibm.websphere.pmi.stat.StatsImpl
                # threadstats=AdminControl.invoke_jmx(perfOName, 'getStatsObject', [threadOName, java.lang.Boolean ('false')], ['javax.management.ObjectName', 'java.lang.Boolean'])
                #statshash=dict(zip(typehash.keys()),[0]*len(typehash.keys()))
                if stats is None:
                    print "No statistics received for %s. Skipping..." % obj
                else:
                    # print "Got %s ..." % obj # = %s..." % (obj,stats.statistics)
                    for s in stats.statistics:
                        statshash[obj+" "+s.name]=get_value(s)
        #print statshash
        print>>f_out,",".join([str(statshash[v]) for v in namelist])
    except:
        # att Printing the traceback may cause memory leaks in Python 2.1 due to circular references. see here http://docs.python.org/library/sys.html
        print "%s. Serious glitch working on %s: %s, %s" % (time.strftime("%m/%d/%Y %H:%M:%S", time.localtime()),obj,sys.exc_info()[0],sys.exc_info()[1])

    time.sleep(float(config['wait'])) # collection delay, convert string to double

    # A procedure for running os commands and capturing the output
    def run(cmd):
      ''' Use Java exec command to run a script due to Jython 2.1 limitations'''
      process = java.lang.Runtime.getRuntime().exec(cmd)
      stdoutstream = ''
      errorstream = ''
      running = 1
      while running:
        while process.getInputStream().available(): # > 0:
            stdoutstream += chr(process.getInputStream().read())
        while process.getErrorStream().available(): # > 0:
            errorstream += chr(process.getErrorStream().read())
        try:
            process.exitValue()
            # OK, we're done simulating:
            running = 0
            #print "done..."
            return (stdoutstream,errorstream)
        except java.lang.IllegalThreadStateException, e:
            # In case of this exception the process is still running.
            #print "running..." # pass
            time.sleep(0.1)

    # take stats collection down if websphere project is down by checing the process state. OS specific
    if os.name=='nt': # do the following on windows
        # check if the parent process is up
        # there is a small bug - sys.argv[0] is the FIRST argument (i.e the real arg, not the script name) under wsadmin, but this is ok here.
        # another small bug - due to the slow cycle time (time.sleep(60)) it may take up to a minute for the stats collection process to go down
        ret1=run("wmic process where (commandline like '%"+sys.argv[0]+"%' and name like 'java.exe') get parentprocessid")
        parentprocessid=re.search(r'\d{2,}',ret1[0]).group(0)
        ret2=run("wmic process where (processid='"+parentprocessid+"') get name")
        if re.match('No Instance.*',ret2[1]):
            print "The parent process is dead. Going down."
            sys.exit(10)
    elif os.name='posix': # to check for Mac add platform.system()=='Darwin'
        pass # do nothing
