@echo off
rem The following batch file is provided for convenience. It allows the jython script to run by either running collectWASPerformanceStats.bat from the command line or by installing it as a Windows service.
rem To run the script with the batch file, create a collectWASPerformanceStats.properties file in the same directory as the jython script and specify the following values:
rem enrole.appServer.path = c:\Program Files\IBM\WebSphere\AppServer\bin
rem enrole.appServer.ejbuser.credentials = WAS admin name (wsadmin)
rem enrole.appServer.ejbuser.principal = WAS admin password

rem By default the statistics is saved into f:\temp\stats.csv. The logs go to f:\temp\stats.log. You can change the location of these files by editing the governor batch.

rem A round-about Microsoft way to get a parameter value
for /f "delims==; tokens=2" %%G in ('findstr enrole.appServer.ejbuser.path collectWASPerformanceStats.properties') do set WASPATH=%%G
for /f "delims==; tokens=2" %%G in ('findstr enrole.appServer.ejbuser.principal collectWASPerformanceStats.properties') do set ADMIN=%%G
for /f "delims==; tokens=2" %%G in ('findstr enrole.appServer.ejbuser.credentials collectWASPerformanceStats.properties') do set ADMINPWD=%%G

echo Starting the statistics collection to f:/temp/stats.csv. Output sent to f:/temp/stats.log. Press ctrl-c to stop ...
echo ------------------------------------------------------- >> f:/temp/stats.log
echo %date% %time%. Starting... >> f:/temp/stats.log
call "%WASPATH%\wsadmin.bat" -lang jython -user %ADMIN% -password %ADMINPWD% -f collectWASPerformanceStats.py f:/temp/stats.csv >> f:/temp/stats.log
echo %date% %time%. Stopped. >> f:/temp/stats.log
