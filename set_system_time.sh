#!/bin/sh

echo "Check the system time"
date
echo "Is the current date and time correct? " ; read -r "[Y/n]:" answer
if [ $answer == "Y" ] ;
then
  echo "Exiting time setting"
  sleep 1
  exit
fi
if [ $answer == "n" ] ;
then
  echo "RTC time is"
  sudo hwclock -r
  echo "Is that time correct? " ; read -r "[Y/n]:" answer
fi
if [ $answer == "Y" ] ;
then
  echo "Applying RTC time to the system"
  sudo hwclock -s
  echo "System time is now:"
  date
  echo "Exiting this shell script"
  sleep 1
  exit
fi
if [ $answer == "n" ] ;
then
  echo "Connect the Central Computer to the internet and wait for its automatic synchronization"
  echo "Or type hereafter the date in the following format: YYYY-MM-DD (2001-09-11)"
  read date_input
  sudo date +%F -s "$date_input"
  echo "Type now the current time in the following format: hh:mm:ss (12:30:55)"
  read time_input
  sudo date +%T -s "$time_imput"
  echo "Time is now:"
  date
  echo "Writing current time inside the RTC"
  sudo hwclock -w
  echo "Exiting this shell script"
  sleep 1
  exit
fi
exit