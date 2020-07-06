# Kivy GUI

The Kivy GUI is used with Electrum on Android devices.
To generate an APK file, follow these instructions.

## Android binary with Docker

This assumes an Ubuntu host, but it should not be too hard to adapt to another
similar system. The docker commands should be executed in the project's root
folder.

#### 1. Install Docker

    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
    sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
    sudo apt-get update
    sudo apt-get install -y docker-ce

#### 2. clone or download repository
    git clone https://github.com/faircoin/electrumfair
    cd electrumfair

#### 3. Build image

    sudo docker build -t electrumfair-android-builder-img electrumfair/gui/kivy/tools

#### 4. Prepare python dependencies

    ./contrib/make_packages

#### 5. Build binaries

##### 5.1 Start docker container

    sudo docker run -it --rm \
        --name electrumfair-android-builder-cont \
        -v $PWD:/home/user/wspace/electrumfair \
        -v ~/.keystore:/home/user/.keystore \
        --workdir /home/user/wspace/electrumfair \
        electrumfair-android-builder-img

This mounts the project dir inside the container,
and so the modifications will affect it, e.g. `.buildozer` folder
will be created.

##### 5.2 make apk - debug version ( for test purposes )

    ./contrib/make_apk

##### 5.3 make apk - release version
If you don't have a keystore file `~/.keystore/electrumfair.keystore` you can create it ( outside the container )  by

    keytool -genkey -v -keystore ~/.keystore/electrumfair.keystore -alias electrumfair -keyalg RSA -keysize 2048 -validity 10000

Now you can make the release

    ./contrib/make_apk release

##### 5.4. The generated binary is in `./bin`.



## FAQ

### I changed something but I don't see any differences on the phone. What did I do wrong?
You probably need to clear the cache: `rm -rf .buildozer/android/platform/build/{build,dists}`


### How do I deploy on connected phone for quick testing?
Assuming `adb` is installed:
```
## install wallet on Android #############################
adb -d install -r ./bin/ElectrumFair-3.3.4.0-release.apk

## run wallet ############################################
adb shell monkey -p org.electrumfair.electrumfair 1

## show live logs ########################################
adb logcat     # ( show all logs )
adb logcat *:W # ( show only warnings and errors )
adb logcat *:E # ( show only errors )
```


### How do I get an interactive shell inside docker?
```
sudo docker run -it --rm \
    -v $PWD:/home/user/wspace/electrum \
    --workdir /home/user/wspace/electrum \
    electrum-android-builder-img
```


### How do I get more verbose logs?
See `log_level` in `buildozer.spec`


### Kivy can be run directly on Linux Desktop. How?
Install Kivy.

Build atlas: `(cd electrum/gui/kivy/; make theming)`

Run electrum with the `-g` switch: `electrum -g kivy`
