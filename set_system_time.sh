#!/bin/sh

printf "Check the system time: "
date
printf "Is the current date and time correct? [Y/n] " ; read -r  answer
if [ $answer == "Y" ] ;
then
  printf "Exiting time setting"
  sleep 1
  exit
fi
if [ $answer == "n" ] ;
then
  printf "RTC time is: "
  sudo hwclock -r
  printf "Is that time correct? [Y/n] " ; read -r answer
fi
if [ $answer == "Y" ] ;
then
  printf "Applying RTC time to the system"
  sudo hwclock -s
  printf "\nSystem time is now "
  date
  printf "Exiting this shell script\n"
  sleep 1
  exit
fi
if [ $answer == "n" ] ;
then
  printf "Is the computer connected to the internet? [Y/n] " ; read -r  answer
  if [ $answer == "Y" ] ;
  then
    printf "Let some time to the system to get time from the internet"
    printf "\nShell script will close\nExecute this script again in one minute\n"
    sleep 5
    exit
  fi
  if [ $answer == "n" ] ;
  then
    printf "Type hereafter the date in the following format: YYYY-MM-DD (2001-09-11): " ; read -r date_input
    sudo date +%F -s "$date_input"
    printf "Type now the current time in the following format: hh:mm:ss (12:30:55): " ; read -r time_input
    sudo date +%T -s "$time_input"
    printf "Date and Time are now: "
    date
    printf "\nWriting current time inside RTC..."
    sudo hwclock -w
    printf "Exiting this shell script\n"
  sleep 1
  exit
  fi
fi
exit