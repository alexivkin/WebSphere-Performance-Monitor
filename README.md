About
-----

This script allows you to collect WebSphere Performance Statistics continuously into a CSV file to analyze later with Excel or a similar tool.
The script is written in jython and runs under the wsadmin shell shipped with all WebSphere distributions. No additional software installation is needed.

The script sits in the background and pulls statistics from a select
number of peformance MBeans provided by WAS. The list of statistics to pull  is
specified in the performance.prop file located in the current folder.
If you want to list all the statistics that is available in your WAS installation, run the script with the -l option at the end.

The script has been tested on AIX and Windows. It can run as a service under Windows, which provides an easy way to start and stop performance monitoring. In order
for it to function as a Windows service the script uses Windows Management Instrumentation (WMI) to monitor parent process and shutdown itself when its parent (service launcher) is terminated.

For more insights on how this script uses the WebSphere Performance Monitoring Interface to pull real-time statistics, look in the [IBM reference document].

Setting it up
-------------

**Windows:** Use the wsadmin.bat located under the default ND deployment manager or a node. For example: c:\Program Files\IBM\WebSphere\AppServer\bin\wsadmin.bat

**AIX/Linux:** Use the wsadmin.sh in your dmgr/nodemanager for an ND deployment, or the server bin folder for a single server install. I.e. /opt/websphere/appserver/bin/wsadmin.sh or /opt/websphere/appserver/profiles/node01/bin/wsadmin.sh

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

Running the collector from a separate server
-------------------------------------------
You can run this remotely from a separate server, or a desktop. For this you need the [thin admin client], IBM JVM Software Development Kit (SDK) and python (any version after 2.1 would do).

- Copy the Administration Thin Client JAR files (com.ibm.ws.admin.clientXXX.jar) from an your WAS environment into the collector box client-folder
- Copy the messages directory from the app_server_root/properties directory to the /client-folder/properties
- Copy the com.ibm.ws.security.crypto.jar file from either the AppServer/plugins directory to /client-folder.
- Copy the soap.client.props, wsjaas_client.conf, ssl.client.props files from the AppServer\profiles\profileName/properties directory to /client-folder/properties. [more info]
- Copy the key.p12 and trust.p12 files from AppServer\profiles\profileName\etc directory to /client-folder/ directory.
Enable the client security by setting the com.ibm.CORBA.securityEnabled property to true. or set the properties in the soap.client.props file in your Java code.
- Use -host *HOSTIP* -port *SOAP_PORT* attributes to wsadmin when running the script

  [enabled]: http://tech.ivkin.net/wiki/IBM_WebSphere_Application_Server_How_To#How_to_enable_WAS_performance_monitoring
  [Windows resource kit]: http://www.microsoft.com/download/en/details.aspx?id=17657
  [thin admin client]: http://pic.dhe.ibm.com/infocenter/wasinfo/v8r0/index.jsp?topic=/com.ibm.websphere.nd.multiplatform.doc/info/ae/ae/txml_adminclient.html
  [more info]: http://pic.dhe.ibm.com/infocenter/wasinfo/v6r1/topic/com.ibm.websphere.express.doc/info/exp/ae/rsec_sslclientpropsfile.html
  [IBM reference document]: http://www-01.ibm.com/support/knowledgecenter/SSEQTP_7.0.0/com.ibm.websphere.nd.doc/info/ae/ae/tprf_command.html
