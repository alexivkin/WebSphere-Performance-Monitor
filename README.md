About
-----

This script allows you to collect WebSphere Performance Statistics continuously into a CSV file to analyze later with Excel or a similar tools.
The script is written in jython and runs under the wsadmin shell  shipped  with
all WebSphere distributions. No additional software installation is needed.

The script sits in the background and pulls statistics from a select
number of peformance MBeans provided by WAS. The list of statistics to pull  is
specified in the performance.prop file located in the current folder.
If you want to list all the statistics that is available in your WAS run the script with the -l option at the end.

The script has been tested on AIX and Windows. It can run as a service under Windows, which provides way to easily start and stop performance monitoring. In order
for it to function as a Windows service the script uses Windows Management Instrumentation (WMI) to monitor parent process and shutdown itself when the parent (wasadmin) is terminated.

Setting it up
-------------

### Windows
Use the wsadmin.bat located under the default ND deployment manager or a node. For example: c:\Program Files\IBM\WebSphere\AppServer\bin\wsadmin.bat

### AIX/Linux
Use the wsadmin.sh in your dmgr/nodemanager for an ND deployment, or the server bin folder for a single server install.
I.e. /opt/websphere/appserver/bin/wsadmin.sh or /opt/websphere/appserver/profiles/node01/bin/wsadmin.sh

-   First, make sure the WebSphere Performance Monitoring Infrastructure is [enabled].
-   Make sure your jython shell is setup properly by running

`wsadmin -lang jython -user *WASADMIN* -password *WASADMINPWD*`

-   In some cases, like when you have security disabled, or running on a node manager, you do not have to specify the was admin and user in the command line.
-   Run the script with the -l option to figure out what statistics you need. There are some sample statistics in the performance.prop file already.

`wsadmin -lang jython -user *WASADMIN* -password *WASADMINPWD* -f collectWASPerformanceStats.py allstats.txt -l`

-   Copy the the specific stats you are interested in from allstats.txt into performance.prop
-   Run the script

`wsadmin -lang jython -user *WASADMIN* -password %ADMINPWD% -f collectWASPerformanceStats.py stats.csv`

How to run this script as a Unix/Linux background command
------
Simply nohup it:

`nohup *PATHTOWSADMIN*/wsadmin.sh -lang jython -f collectWASPerformanceStats.py stats.csv &`

You could also do a daily rollover:


How to install the script as a Windows service
----------------------------------------------
-   Get and install the [Windows resource kit]
-   Run the following (adjust the paths to match your installation)

`instsrv.exe "WebSphere Performance Monitor" "C:\Program Files\Windows Resource Kits\Tools\srvany.exe"`

-   Create the Parameters key in HKEY\LOCAL\MACHINE\\SYSTEM\\CurrentControlSet\\Services\\WebSphere Performance
- Add the Application string value under HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\WebSphere Performance Monitor\Parameters that reads

`cmd /c PATHTOSCRIPT\collectWASPerformanceStats.bat`

 - Create a collectWASPerformanceStats.properties file in the same directory as the jython script and specify the following values

```
enrole.appServer.path = WAS path, e.g. c:\Program Files\IBM\WebSphere\AppServer\bin
enrole.appServer.ejbuser.credentials = WAS admin name (wsadmin)
enrole.appServer.ejbuser.principal = WAS admin password`
```
- Start the service

  [enabled]: http://tech.ivkin.net/wiki/IBM_WebSphere_Application_Server_How_To#How_to_enable_WAS_performance_monitoring
  [Windows resource kit]: http://www.microsoft.com/download/en/details.aspx?id=17657
