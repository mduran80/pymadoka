## PyMadoka

This library has been written to control the thermostat Daikin BRC1H family without the need to use the mobile Madoka apps.

The code is based on the previous work by Benjamin Lafois (both [reverse engineering](https://github.com/blafois/Daikin-Madoka-BRC1H-BLE-Reverse) and [OpenHAB add-on](https://github.com/openhab/openhab-addons/tree/main/bundles/org.openhab.binding.bluetooth.daikinmadoka/src/main/java/org/openhab/binding/bluetooth/daikinmadoka)).

What does it provide?

* A Python library that can be used to integrate it with home automation systems (HomeAssistant)
* CLI command to control the device


## Requirements

The library has been developed and tested on Linux. 

Once the thermostat has been paired and connected to a client, it is not available during a devices scan. Therefore, the library usually enforces a "disconnect" of the current client so it can be listed and become available for connection. I have not been able to find the way to do it using the [BLE library](https://github.com/hbldh/bleak) so it relays on `bluetoothctl` to do it.

However, this `bluetoothctl` dependency results in a lack of compatibility with other operating systems, so only Linux is supported at the moment.

**No other client must be connected to the device (even using the same Bluetooth adapter).** 

**This library has been designed to operate exclusively with the device and messages coming as a response of commands issued to the device from other clients may interfer with the behaviour.**


## Pairing the device

As previously noted, the device has to be paired in order to work and it requires code confirmation on the screen. The best way to achieve it is to follow this steps:

* Disconnect the BRC1H from any other device by accessing the setup menu and pressing the "forget bluetooth connection" button
* Execute `bluetoothctl`
* `agent off` to disable default bluetooth agent
* `agent KeyboardDisplay` to enable bluetooth agent for pairing
* `scan on` and wait 5s. The device MAC should be listed 
* `scan off`
* `pair <MAC_ADDRESS>`. You will be prompted to confirm the code. After typing yes, you will have to confirm on the BRC1H screen.


## Command line usage

The package provides a stand-alone CLI application that can be used to control the device. It outputs all the results in a convenient JSON format and can be configured using the following switches:

```
Usage: pymadoka [OPTIONS] COMMAND [ARGS]...

Options:
  -a, --address TEXT              [required]
  --force-disconnect / --not-force-disconnect
  -t, --device-discovery-timeout INTEGER RANGE
  -o, --log-output PATH
  --debug
  -v, --verbose
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

  * -a: BRC1H address.
  * --force-disconnect/--no-force-disconnect: Control if the device has to be disconnected to force a rediscovery
  * -t: Device discovery timeout or for how long the scan must be run
  * -o: Redirect logging to file output
  * --debug: Enable debug logging
  * -v: Verbose logging. This must be enabled if file output and debug options are to be used

  Output example:

```
{"cooling_fan_speed": "HIGH", "heating_fan_speed": "LOW"}
```

## Library usage

The main class is Controller. The Controller contains features that are used to control different aspects of the device such as: set point, fan speed, operation mode and others.

Each feature has two methods (when available):

* Query: query the device for the information related to the feature
* Update: update the device with the new feature status

Check the examples folder for more details.

## Troubleshooting

* **My device is not listed when I scan for devices using `bluetoothctl`**

Check that the BR1CH is not connected to any other device. Go to BR1CH screen, tap on the menu and look for the Bluetooth settings. Tap on disconnect.

* **My client keeps disconnecting some seconds after connecting**

Check that your devices are correctly paired (`bluetoothctl paired-devices`). If your device is not listed and you are not able to pair after several tries, it may be due to a failure on DBUS-Bluez service. You can try to restart the service by issuing:

```
sudo systemctl restart dbus-org.bluez.service
```

* **It takes several seconds to execute each command**

The execution of a single command takes some time as it has to follow several steps before it can write the command:

1. Disconnect 
2. Discover devices/list services
3. Connect
4. Issue command
5. Wait for response
