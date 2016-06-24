#!/bin/bash
echo 'Downloading a list of all the modules...'
wget https://downloads.tryton.org/modules.txt

for i in $( cat modules.txt )
do
        echo ' '
        echo 'Cloning '$i
        git clone https://github.com/tryton/$i
        
        echo 'Checking out to 4.0 version'
        cd $i
        git checkout 4.0.0 && git checkout 4.0.1 && git checkout 4.0.2 && git checkout 4.0.3 && git checkout 4.1.0 && git checkout 4.1.1
        cd ..
done

echo 'Cleaning modules.txt file...'
rm modules.txt
