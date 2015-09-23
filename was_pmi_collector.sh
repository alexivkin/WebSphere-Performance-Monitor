#!/bin/sh
# Written for korn shell

# code location
CODEDIR=/opt/ibm/webphere/bin/monitor
DATADIR=/opt/ibm/webphere/pmi/
WSADMIN=/opt/ibm/websphere/appserver/profiles/node01/bin/wsadmin.sh
pidfile=$CODEDIR/collectwaspmi.pid

start() {
  savepid
  date=`date +%Y-%m-%d`
  pid=""
  if [ -s $pidfile ];  then
    pid=`cat $pidfile`
  fi
  if [ -z "$pid" ];  then
    cmd="$WSADMIN -lang jython -f $CODEDIR/collectWASPerformanceStats.py $DATA/$date.csv"
    nohup $cmd
  else
    echo "Already running"
  fi
}

stop() {
  savepid
  pid=""
  if [ -s $pidfile ];  then
    pid=`cat $pidfile`
  fi
  if [ -n "$pid" ]; then
    kill -TERM $pid
  else
    echo "Not running"
  fi
}

savepid() {
  echo `ps aux | grep "collectWASPerformanceStats.py" | grep -v grep | grep java | awk '{ print $2 }'` > $pidfile
}


cd $CODEDIR
for arg in $*; do
  case $arg in
  start)
    echo "Starting..."
    start
    sleep 15
    savepid
    ;;
  stop)
    echo "Stopping..."
    stop
    ;;
  esac
done
