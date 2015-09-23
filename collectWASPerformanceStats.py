'''
Queries current running WAS stats and saves them to a file
(C) 2015 Alex Ivkin

Run using the following command:
wsadmin.[bat|sh] -lang jython -user wsadmin -password wsadmin -f collectWASPerformanceStats.py <stats_file> [-l]

You can omit -user and -password. wsadmin is in \Program Files\IBM\WebSphere\AppServer\bin\ on a default windows installation

NOTE: On Windows, due to WebSphere weirdness you have to use FORWARD slashes (/) in the output file name. Otherwise the backward slashes (\) need to be doubled or they will turn into escape sequences

Use -l after the output file name to export the list of all available performance MBeans to the output file and quit

Style note: Jython notation allows the use of shortened get/set functions for java objects, e.g using .list, instead of getList(), or .attribute=1 instead of ,setAttribute(1). 
However I try to stay with the java style get/set here to signify a python object vs java object

'''
import re,sys,time,os,java
import com.ibm.websphere.pmi.stat.WSStatsHelper as WSStatsHelper
#import java.util.Locale as Locale

if len(sys.argv)==0:
    print __doc__
    sys.exit(1)

print "Initializing..."
# script config
scriptconfig={} 

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
        #init the configs
        #WSStatsHelper.initTextInfo(AdminControl.invoke_jmx(perfObjectName, 'getConfigs', [None], ['java.util.Locale']),None)   # not all stats config files are in the classpath. WSStatsHelper helps init descriptions for PMIModuleConfigs that are not bundled with WAS but are added later. Second argument is None for the default locale (Locale.getDefault())

print "Performance beans found: %s" % ",".join(perfHash.keys())

# Enable PMI data using the pre-defined statistic sets.
#AdminControl.invoke_jmx (perfObjName, 'setStatisticSet', ['all'], ['java.lang.String']) #@UnusedVariable @UndefinedVariable

# Return a string with all the sub-statistics and their metrics listed recursively in a multi-line string
def getSubStatsDesc(stats,prefix,level): 
    ret = ""
    if level: 
        if prefix:  
            prefix="%s>%s" % (prefix,stats.getName()) # keep recording sublevels
        else: # dont start the first level prefix with a separator
            prefix="%s" % stats.getName()
    else: # dont record the root level (0) prefix
        prefix=""
    substats=stats.getSubStats()
    if substats is not None:
        for sub in substats:
            subDesc=getSubStatsDesc(stats.getStats(sub.getName()),prefix,level+1)
            if prefix:
                name="%s>%s" % (prefix,sub.getName())
            else: # dont start the first level prefix with a separator
                name=sub.getName()
            ret="%s\n%s>>>%s%s" % (ret," "*25,name,subDesc) #"/"*level for a simple prefix, ",".join([str(s) for s in sub.getStatisticNames()]) for the actual statistics
    return ret

def clean(name):    # remove substrings per the config file from the given string
    if "clean" in scriptconfig.keys():
        if "," in scriptconfig["clean"]['value']:
            for s in scriptconfig["clean"]['value'].split(","):
                name=name.replace(s,"")
        else:
            name=name.replace(scriptconfig["clean"]['value'],"")
    return name

# Return an hash with all the sub-statistics, and their values retreived recursively
def getSubStatsHash(stats,ret,prefix): 
    #print prefix
    if prefix:  
        prefix="%s>%s" % (prefix,clean(stats.getName())) # keep recording sublevels
    else: # dont start the first level prefix with a separator
        prefix="%s" % clean(stats.getName())
    # collect all the same level statistics
    for s in stats.getStatistics():
        ret[prefix+" "+clean(s.getName())]=s # hasing the stat object as is, it will have to be processed via get_value later
    substats=stats.getSubStats() 
    if substats is not None:
        for sub in substats:
            allsubstats=getSubStatsHash(stats.getStats(sub.getName()),ret,prefix)
            #print allsubstats
            ret.update(allsubstats)
    return ret

# init the configs
# queriying the first available perfmbean they all return the same set of performance metrics
configs=AdminControl.invoke_jmx(perfHash[perfHash.keys()[0]], 'getConfigs', [None], ['java.util.Locale'])  # returns an array of all PmiModuleConfig objects, None for the server default locale means 'use default'
WSStatsHelper.initTextInfo(configs,None)   # not all stats config files are in the classpath. WSStatsHelper helps init descriptions for PMIModuleConfigs that are not bundled with WAS but are added later. Second argument is None for the default locale (Locale.getDefault())

if len(sys.argv) > 1 and sys.argv[1]=='-l':
    # list objects with stats
    f_out=open(sys.argv[0],"w")
    statName={}
    subStats={}
    statDescription={}
    print "Listing modules ..."
    for config in configs:
        if config is not None: # record the config specs, if we have not already seen it
            statDescription[config.getShortName()]=[config.getDescription(), ",".join([d.name for d in config.listAllData()])]
    print "Listing objects ..."
    for a in AdminControl.queryNames('*').split('\n'): #type=ConnectionPool, @UndefinedVariable
        obj=AdminControl.makeObjectName(a)
        process=obj.getKeyProperty("process")
        subs=""
        if process is None:
            desc="*No process"
        else:
            if process not in perfHash.keys(): # desc="*No perfmbean %s" % process
                process=perfHash.keys()[0] # ask the first perfmbean
            config=AdminControl.invoke_jmx(perfHash[process], 'getConfig', [obj], ['javax.management.ObjectName'])  # returns PmiModuleConfig object
            if config is not None: # record the config specs, if we have not already seen it
                desc=config.getShortName()
            else:
                #desc="*Blank"
                continue # no use in recording non-stat objects
            # now get and record all sub-statistics available under that object
            stats=AdminControl.invoke_jmx(perfHash[process], 'getStatsObject', [obj,java.lang.Boolean('true')], ['javax.management.ObjectName','java.lang.Boolean'])  # returns WSStats object
            if stats is not None and stats.getSubStats() is not None:
                subs=getSubStatsDesc(stats,"",0)
                #printStats(stats,1)
        statName[a]=desc
        subStats[a]=subs
    print "Writing performance beans descriptions..."
    print >> f_out, "Available performance sources aka perfmbeans (process:name [enabled statistic set]):"
    skeys=perfHash.keys()
    skeys.sort()
    for s in skeys:
         print >> f_out, "%-25s:%s [%s]" % (s,perfHash[s],AdminControl.invoke_jmx(perfHash[s], 'getStatisticSet', [],[]))
    f_out.flush()
    print "Writing stat descriptions..."
    print >> f_out, "\nAvailable performance modules (module-description [provided statistics]):"
    skeys=statDescription.keys()
    skeys.sort()
    for s in skeys:
         print >> f_out, "%-25s-%s [%s]" % (s,statDescription[s][0],statDescription[s][1])
    f_out.flush()
    print "Writing stat names..."
    print >> f_out, "\nPMI Managed objects (module=full managed object name):"
    skeys=statName.keys()
    skeys.sort() # sort() does not return a list but does sorting in place, hence the ugly multi-liner
    for s in skeys:
         print >> f_out, "%-25s=%s%s" % (statName[s], s,subStats[s])
    print "done."
    f_out.close()
    sys.exit(0)

# load config
try:
    for line in open("performance.prop","r").readlines():
       line=line.strip()
       if not line.startswith("#") and "=" in line:
            configkey=line.split("=",1)[0].strip()
            mbean=line.split("=",1)[1].strip()
            if mbean.find(">>>") != -1:     # split in two, the latter half is a substatistics
                (mbean,substat)=mbean.split(">>>")
            else:
                substat=""
            scriptconfig[configkey]={'value':mbean,'substat':substat}
       
    print "Loaded %s settings." % len(scriptconfig.keys())
except:
    print "performance.prop can't be loaded: %s" % sys.exc_info()[0]
    sys.exit(1)

# convert conf into wasobjects and create a header
WASobjects={}
#statsize={}         # track the number of individual statistics in each perf object. Useful for maintaining proper CSV line in case some stats need to be skipped
namelist=[] # list is used for ordering, hashtables are unordered
configkeys=scriptconfig.keys()
configkeys.sort()
for c in configkeys:
    if c == "wait" or c == "clean":     # skip the control config lines, since it's not a watched stat
        continue
    try:
        WASobjects[c]=AdminControl.makeObjectName(AdminControl.completeObjectName(scriptconfig[c]['value'])) 
        # we can get the pmiconfig from any object (e.g perfHash[perfHash.keys()[0]]), but will try to be precise here
        process=WASobjects[c].getKeyProperty("process")
        if process is None:
            print "No process definition for %s. Skipping..." % WASobjects[c]
            continue
        elif process not in perfHash.keys():
            print "Metrics process %s for %s has no matching perfomance bean to pull from. Skipping..." % (process,WASobjects[c])
            continue
        statconfig=AdminControl.invoke_jmx(perfHash[process], 'getConfig', [WASobjects[c]], ['javax.management.ObjectName']) 
        #WSStatsHelper.initTextInfo([statconfig],None)   # not all stats config files are in the classpath. WSStatsHelper helps init descriptions for PMIModuleConfigs that are not bundled with WAS but are added later. Second argument is None for the default locale (Locale.getDefault())
        if statconfig is None:
            print "Empty stat config for %s. Skipping..." % c
            continue
        #statsize[c]=0
        stats=AdminControl.invoke_jmx(perfHash[process], 'getStatsObject', [WASobjects[c],java.lang.Boolean('true')], ['javax.management.ObjectName','java.lang.Boolean']) 
        if stats is None:
            print "No stats found for %s" % c
            continue
        if scriptconfig[c]['substat']: # get the substats
            if stats.getStats(scriptconfig[c]['substat']) is None:
                print "No substat %s in %s" % (scriptconfig[c]['substat'], c)
            else:
                allsubstats=getSubStatsHash(stats.getStats(scriptconfig[c]['substat']),{},None) # recursive search
                print "Found %s substats for %s in %s" % (len(allsubstats.keys()),scriptconfig[c]['substat'],c)
                for s in allsubstats.keys():
                    namelist.append(c+" "+s)
        else:
            # by pooling the actual stats object, and not the conf object we are ensuring that we get only actually provided statistics, not advertised statistics
            #for d in statconfig.listAllData():
            for s in stats.getStatistics(): 
                #statsize[c]+=1
                namelist.append(c+" "+s.getName())
    except:
        print "Problem looking up %s: %s, %s. Skipping..." % (c,sys.exc_info()[0],sys.exc_info()[1])

# Simulate CSV. csv library may not be available in WAS's outdated jython
# namesort is ordered and determines the order of fields in the csv
namelist.sort()
namelist.insert(0,'Time')
namelist.insert(0,'Date')
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

# decode value based on the stat type
def get_value(s):
    value="."
    if str(s.getClass())=='com.ibm.ws.pmi.stat.BoundedRangeStatisticImpl': # bounded range
        value=s.getCurrent()
    elif str(s.getClass())=='com.ibm.ws.pmi.stat.CountStatisticImpl': # count statistics
        value=s.getCount()
    elif str(s.getClass())=='com.ibm.ws.pmi.stat.DoubleStatisticImpl':
        value=s.getDouble()
    elif str(s.getClass())=='com.ibm.ws.pmi.stat.TimeStatisticImpl':  # max, min, minTime,maxTime, totalTime, sumOfSquares, delta, mean
        value=s.getCount()
    elif str(s.getClass())=='com.ibm.ws.pmi.stat.RangeStatisticImpl':   # lowWaterMark, highWaterMark, integral, delta, mean, current
        value=s.getCurrent()
    elif str(s.getClass())=='com.ibm.ws.pmi.stat.AverageStatisticImpl': # max, mean,min,sumOfSquares,total
        value=s.getCount()
    else:
        value=s.getClass() # .class works too
    return value

print "Pulling Websphere statistics...Press Ctrl-C to interrupt"

while 1:
    try:
        statshash={}
        for t in namelist: # pre-init stats
            if t=="Date":
                statshash[t]=time.strftime("%m/%d/%Y", time.localtime())
            elif t=="Time":
                statshash[t]=time.strftime("%H:%M:%S", time.localtime())
            else:
                statshash[t]=""
        print "%s %s Collecting statistics ..." % (statshash["Date"],statshash["Time"])
        for obj in WASobjects.keys():  # the sorting is not really required because the ordering in CSV is controlled by the ordering in namelist
            process=WASobjects[obj].getKeyProperty("process")
            if process is None:
                print "No process definition for %s. Skipping..." % obj
                continue
            elif process not in perfHash.keys():
                print "Metrics process %s for %s has no matching perfomance bean to pull from. Skipping..." % (process,obj)
                continue
            # pull actual statistics from the associated performance bean
            stats=AdminControl.invoke_jmx(perfHash[process], 'getStatsObject', [WASobjects[obj], java.lang.Boolean ('true')], ['javax.management.ObjectName', 'java.lang.Boolean']) # second argument pulls recursive substats. returns com.ibm.websphere.pmi.stat.StatsImpl or WSStats wor stat.Stats
            #statshash=dict(zip(typehash.keys()),[0]*len(typehash.keys()))
            if stats is None:
                print "No statistics received for %s. Skipping..." % obj
                continue
            if scriptconfig[obj]['substat']: # get the substats
                if stats.getStats(scriptconfig[obj]['substat']) is not None:
                    allsubstats=getSubStatsHash(stats.getStats(scriptconfig[obj]['substat']),{},None) # recursive search
                    for s in allsubstats.keys():
                        statshash[obj+" "+s]=get_value(allsubstats[s])
            else: # no substats
                # print "Got %s ..." % obj # = %s..." % (obj,stats.statistics)
                for s in stats.getStatistics():
                    statshash[obj+" "+s.name]=get_value(s)
        #print statshash
        print>>f_out,",".join([str(statshash[v]) for v in namelist])
    except:
        # att Printing the traceback may cause memory leaks in Python 2.1 due to circular references. see here http://docs.python.org/library/sys.html
        print "%s. Serious glitch working on %s: %s, %s, line %s" % (time.strftime("%m/%d/%Y %H:%M:%S", time.localtime()),obj,sys.exc_info()[0],sys.exc_info()[1],sys.exc_info()[2].tb_lineno)
    
    time.sleep(float(scriptconfig['wait']['value'])) # collection delay, convert string to double

    # take stats collection down if websphere project is down by checing the process state. OS specific
    # check if the parent process is up
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
    elif os.name=='posix': # to check for Mac add platform.system()=='Darwin'
        pass # do nothing
