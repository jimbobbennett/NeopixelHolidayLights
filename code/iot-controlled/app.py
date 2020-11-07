import asyncio
import board
import neopixel
import os
from azure.iot.device.aio import IoTHubDeviceClient, ProvisioningDeviceClient
from azure.iot.device import MethodResponse
from dotenv import load_dotenv

# Define the NeoPixel strip setting the pin the control wire is connected to, the brightness
# and if the colors are written as soon as the values are updated, or if they need to be 
# updated all at once as soon as the values are set
pixels = neopixel.NeoPixel(board.D18, 150, brightness=0.2, auto_write=False)

# Load the IoT Central connection details from a .env file
load_dotenv()
id_scope = os.getenv('ID_SCOPE')
device_id = os.getenv('DEVICE_ID')
primary_key = os.getenv('PRIMARY_KEY')

# Declare the device client so it can be used from all the function
device_client = None

# Provisions the device with the Azure device provisioning service or returns
# the connection details if the device is already provisioned
async def register_device():
    provisioning_device_client = ProvisioningDeviceClient.create_from_symmetric_key(
        provisioning_host='global.azure-devices-provisioning.net',
        registration_id=device_id,
        id_scope=id_scope,
        symmetric_key=primary_key,
    )

    return await provisioning_device_client.register()

# Sets the color of the Neopixels based on a color string coming in.
# This color string is a 6 character code, 2 characters for red, 2 for green
# and 2 for blue. These 2 characters are a HEX value from 00 to FF.
# For example FF0000 is full red, no green or blue. FFFFFF is white, 000000 is off.
# Once the color is set, write it back to the IoT Central property via a device twin
async def set_color(color):
    # split in the color string into the red, green and blue components, and convert these
    # to valid hex strings
    r = '0x' + color[0:2]
    g = '0x' + color[2:4]
    b = '0x' + color[4:6]

    # Convert hext to numerical values
    r_value = int(r, 0)
    g_value = int(g, 0)
    b_value = int(b, 0)

    print('Updating color: r =', r_value, ', g =', g_value, ', b =', b_value)

    # Set all the pixels to the new color
    pixels.fill((r_value, g_value, b_value))

    # Show the color on all the pixels
    pixels.show()

    # Write the color back as a property
    # Properties are written to the device twin, so patch the reported properties
    # with the color
    patch = {'Color':color}
    print("Sending patch:", patch)
    await device_client.patch_twin_reported_properties(patch)

# IoT Central command handler
# IoT Central commands are implemented as IoT Hub direct methods
async def command_handler(method_request):
    print("Message received:", method_request.name)
    print("Message payload:", method_request.payload)

    # Determine how to respond to the command based on the IoT Hub direct method method name
    # which is the same as the IoT Central command name
    if method_request.name == "On":
        # For an On request, set the color based on the payload
        await set_color(method_request.payload)
        print("executed on")
    elif method_request.name == "Off":
        # For an Off request, set the color to 000000, which turns the pixels off
        await set_color("000000")
        print("executed off")
    else:
        print("Received unknown method: " + method_request.name)

    # Method calls have to return a response so IoT Central knows it was handled correctly,
    # So send a 200 response to show we handled this
    payload = {"result": True}
    status = 200

    # Send the response
    method_response = MethodResponse.create_from_method_request(method_request, status, payload)
    await device_client.send_method_response(method_response)

async def property_handler(patch):
    print("Patch received:", patch)
    if 'Color' in patch:
        await set_color(patch['Color'])

# The main async function that runs the app
async def main():
    global device_client
    
    # Regsiter the Pi as an IoT device in IoT Central
    registration_result = await register_device()

    # Build the IoT Hub connection string from the registration details
    # IoT Central sits on top of IoT Hub, and the Python SDK only supports IoT Hub,
    # So to talk to IoT central the IoT Hub connection string needs to be built from details
    # from registering the device with the provisioning service
    conn_str='HostName=' + registration_result.registration_state.assigned_hub + \
                ';DeviceId=' + device_id + \
                ';SharedAccessKey=' + primary_key

    # The client object is used to interact with your Azure IoT Central app via IoT Hub, so create this 
    # from the connection string
    device_client = IoTHubDeviceClient.create_from_connection_string(conn_str)

    # Connect the client to IoT Hub
    print('Connecting')
    await device_client.connect()
    print('Connected')

    # IoT Central stores properties in the device twin, so read this to see if we have a color
    # stored from the last run for the lights. This way when the device starts up it can set the color
    # to the last setting
    twin = await device_client.get_twin()
    print('Got twin: ', twin)

    # Load the color from the reported properties of the twin if it exists
    if 'reported' in twin and 'Color' in twin['reported']:
        await set_color(twin['reported']['Color'])

    # Set the method request handler on the client to handle IoT Central commands
    device_client.on_method_request_received = command_handler

    # Handle updates to the color property from IoT Central
    device_client.on_twin_desired_properties_patch_received = property_handler

    # Define a message loop that keeps the app alive whilst listening for commands
    async def main_loop():
        while True:
            await asyncio.sleep(1)

    # Wait for user to indicate they are done listening for method calls
    await main_loop()

    # Finally, disconnect
    await device_client.disconnect()

# Start the async app running
if __name__ == "__main__":
    asyncio.run(main())