# PyMadoka

This library has been written to control the thermostat Daikin BRC1H family without the need to use the mobile Madoka apps.

The code is based on the previous work by Benjamin Lafois (both [reverse engineering](https://github.com/blafois/Daikin-Madoka-BRC1H-BLE-Reverse) and [OpenHAB add-on](https://github.com/openhab/openhab-addons/tree/main/bundles/org.openhab.binding.bluetooth.daikinmadoka/src/main/java/org/openhab/binding/bluetooth/daikinmadoka)).

What does it provide?

* A Python library that can be used to integrate it with home automation systems (HomeAssistant)
* CLI tool to control the device (pymadoka)
* CLI tool to bridge the device with MQTT (pymadoka-mqtt)


# Installation
```
pip install pymadoka
```
# Requirements

The library has been developed and tested on Linux Python 3.

Once the thermostat has been paired and connected to a client, it is not available during a devices scan. Therefore, the library usually enforces a "disconnect" of the current client so it can be listed and become available for connection. I have not been able to find the way to do it using the [BLE library](https://github.com/hbldh/bleak) so it relays on `bluetoothctl` to do it.

However, this `bluetoothctl` dependency results in a lack of compatibility with other operating systems, so only Linux is supported at the moment. Nevertheless, the "force disconnect" might be only required on Linux and can be disabled when testing other operating systems.

**No other client must be connected to the device (even using the same Bluetooth adapter).** 

**This library has been designed to operate exclusively with the device and messages coming as a response of commands issued to the device from other clients may interfer with the behaviour.**


# Pairing the device

As previously noted, the device has to be paired in order to work and it requires code confirmation on the screen. The best way to achieve it is to follow this steps:

* Disconnect the BRC1H from any other device by accessing the setup menu and pressing the "forget bluetooth connection" button
* Execute `bluetoothctl`
* `agent off` to disable default bluetooth agent
* `agent KeyboardDisplay` to enable bluetooth agent for pairing
* `scan on` and wait 5s. The device MAC should be listed 
* `scan off`
* `pair <MAC_ADDRESS>`. You will be prompted to confirm the code. After typing yes, you will have to confirm on the BRC1H screen.


# Command line usage

## pymadoka 

The package provides a stand-alone CLI tool (pymadoka) that can be used to control the device. It outputs all the results in a convenient JSON format and can be configured using the following switches:

```
$ pymadoka

Usage: pymadoka [OPTIONS] COMMAND [ARGS]...

Options:
  -a, --address TEXT              Bluetooth MAC address of the thermostat
                                  [required]

  -d, --adapter TEXT              Name of the Bluetooth adapter to be used for
                                  the connection  [default: hci0]

  --force-disconnect / --not-force-disconnect
                                  Should disconnect the device to ensure it is
                                  recognized (recommended)  [default: True]

  -t, --device-discovery-timeout INTEGER
                                  Timeout for Bluetooth device scan in seconds
                                  [default: 5]

  -o, --log-output PATH           Path to the log output file
  --debug                         Enable debug logging
  --verbose                       Enable versbose logging
  --version                       Show the version and exit.
  --help                          Show this message and exit.

Commands:
  get-clean-filter-indicator
  get-fan-speed
  get-operation-mode
  get-power-state
  get-set-point
  get-status
  get-temperatures
  set-fan-speed
  set-operation-mode
  set-set-point
```
Output example:

```
{"cooling_fan_speed": "HIGH", "heating_fan_speed": "LOW"}
```

## pymadoka-mqtt

This tool is intended to be used as a daemon. It helps to integrate the library into home automation systems that support MQTT climate devices. It requires a configuration file to specify all the MQTT supported features:

```yaml
mqtt:
    host: "localhost"
    port: 1883
    username: "myuser"
    password: "mypassword"
    ssl: False
    root_topic: "/my_root_topic" # Default root topic is /madoka
daemon:
    update_interval: 15 # Query the device at this interval
```

This is an example of the data sent with each status message:

```json

$ mosquitto_sub -t "#"

{"fan_speed": {"cooling_fan_speed": "LOW", "heating_fan_speed": "LOW"}, "operation_mode": {"operation_mode": "AUTO"}, "power_state": {"turn_on": false}, "set_point": {"cooling_set_point": 17, "heating_set_point": 17}, "temperatures": {"indoor": 20, "outdoor": null}, "clean_filter_indicator": {"clean_filter_indicator": false}}

```
Usage:

```
$ pymadoka-mqtt --help
Usage: pymadoka-mqtt [OPTIONS]

Options:
  -a, --address TEXT              Bluetooth MAC address of the thermostat
                                  [required]

  -c, --config PATH               MQTT config file  [required]
  -d, --adapter TEXT              Name of the Bluetooth adapter to be used for
                                  the connection  [default: hci0]

  --force-disconnect / --not-force-disconnect
                                  Should disconnect the device to ensure it is
                                  recognized (recommended)  [default: True]

  -t, --device-discovery-timeout INTEGER
                                  Timeout for Bluetooth device scan in seconds
                                  [default: 5]

  -o, --log-output PATH           Path to the log output file
  --debug                         Enable debug logging
  --verbose                       Enable versbose logging
  --version                       Show the version and exit.
  --help                          Show this message and exit.
```

# Library usage

The main class is Controller. The Controller contains features that are used to control different aspects of the device such as: set point, fan speed, operation mode and others.

Each feature has two methods (when available):

* Query: query the device for the information related to the feature
* Update: update the device with the new feature status

Check the examples folder for more details.

# Supporting new features

This library has been implemented to cover the basics of the HVAC. The official Madoka app seems to offer different GUIs according to the features of the HVAC model being controlled and mine doesn't seem to be as complex as others are. However, in the case you are interested in supporting other features, you can contribute by reverse engineering the Bluetooth messages required to control those features. 

There are several ways to do it but one of the easiest is to snoop on the Bluetooth interface and capture all the traffic:
* [Android bluetooth debugging](https://source.android.com/devices/bluetooth/verifying_debugging). By the end of the chapter, it explains how to enable Bluetooth Snoop logs 
* [iOS bluetooth debugging](https://www.bluetooth.com/blog/a-new-way-to-debug-iosbluetooth-applications/). 

Also, it is important to check the `btmon` utility as it can help with the message debugging on Linux. 

Search for sent/received messages
```
$ sudo btmon | grep -C 5 ACL
```

# Troubleshooting

* **My device is not listed when I scan for devices using `bluetoothctl`**

Check that the BR1CH is not connected to any other device. Go to BR1CH screen, tap on the menu and look for the Bluetooth settings. Tap on disconnect.

* **My client keeps disconnecting some seconds after connecting**

Check that your devices are correctly paired (`bluetoothctl paired-devices`). If your device is not listed and you are not able to pair after several tries, it may be due to a failure on DBUS-Bluez service. You can try to restart the service by issuing:

```
$ sudo systemctl restart dbus-org.bluez.service
```

* **It takes several seconds to execute each command**

The execution of a single command takes some time as it has to follow several steps before it can write the command:

1. Disconnect 
2. Discover devices/list services
3. Connect
4. Issue command
5. Wait for response

# TODO

1. Implement a BLE emulator or a Frida script to activate the app features not shown for the device
