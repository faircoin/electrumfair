# Android APK build
Build instructions ( compact )  

~~~
#################################################################################
### download / clone repository  ################################################
git clone https://github.com/faircoin/electrumfair
cd electrumfair

#################################################################################
### build docker image ##########################################################
sudo docker build -t electrumfair-android-builder-img electrumfair/gui/kivy/tools

#################################################################################
### prepare dependencies ########################################################
./contrib/make_packages

#################################################################################
### run docker container and make debug and release version #####################
sudo docker run -it --rm \
    --name electrumfair-android-builder-cont \
    -v $PWD:/home/user/wspace/electrumfair \
    -v ~/.keystore:/home/user/.keystore \
    --workdir /home/user/wspace/electrumfair \
    electrumfair-android-builder-img

### run make inside docker container
./contrib/make_apk            # make debug version
./contrib/make_apk release    # make release version
~~~



~~~
## install wallet on Android #############################
adb -d install -r ./bin/ElectrumFair-3.3.4.0-release.apk

## run wallet ############################################
adb shell monkey -p org.electrumfair.electrumfair 1

## show live logs ########################################
adb logcat     # ( show all logs )
adb logcat *:W # ( show only warnings and errors )
adb logcat *:E # ( show only errors )
adb logcat | grep python # ( show only logs contains python )
~~~
