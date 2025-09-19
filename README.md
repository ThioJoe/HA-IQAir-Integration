# Home Assistant IQAir Cloud Integration

A Home Assistant integration for controlling IQAir air purifiers via the IQAir Cloud API.

NOTES: 
- This requires a device that can connect to WiFi and supports the IQAir Cloud API. I have not figured out a way to control it purely locally.
- I made this using my "GC Multigas XE" device as reference, it might not support all features of other devices. Post an issue thread if you run into issues.
- This uses undocumented Cloud APIs so might not work perfectly forever if something changes on the back end.
- I don't know how long the auth tokens last but I haven't had them expire yet. They might stop working if you actually click logout in the dashboard.

## Features

- **Fan Control**: Turn the device on/off and set the fan speed.
- **Switch Entities**:
    - Toggle Smart Mode (Auto Mode).
    - Enable/disable the Control Panel Lock.
    - Turn the Display Light on or off.
- **Select Entities**:
    - Choose the Smart Mode Profile (e.g., Quiet, Balanced, Max).
    - Adjust the Display Brightness level.

## Installation

### HACS Custom Repository Install (Recommended - To know about updates)

1. Within the HACS page, click the menu at the top right > then click "Custom Repositories".
2. Within the "Repository Field" enter `ThioJoe/HA-IQAir-Integration` . For the "Type" field select "Integration"
3. Search / filter for the one called "IQAir Cloud Integration" and click it. Then install by clicking the "Download" button.
4. Reboot Home Assistant. For setup, see the sections below titled "Configuration" and "Acquiring the Tokens".

### Manual Installation

1.  Copy the `iqair_cloud` folder from this repository into your Home Assistant `custom_components` directory.
2.  Restart Home Assistant.

## Configuration

1.  Navigate to **Settings** > **Devices & Services** in Home Assistant.
2.  Click the **Add Integration** button.
3.  Search for "IQAir Cloud" and select it.
4.  Enter the following information when prompted (see instructions in next section for how to acquire them):
    -   **Auth Token**: Your IQAir API authorization bearer token.
    -   **Login Token**: Your IQAir `x-login-token`.
    -   **User ID**: Your IQAir User ID.
5.  The integration will discover your devices. Select the device you wish to add.

## Acquiring the Tokens

### Prepare: Opening the Chrome Dev Tools
1. First log into the IQAir Dashboard with your account to which your device is registered: [dashboard.iqair.com/](https://dashboard.iqair.com/)
2. Press F12 in your browser to open the dev tools and go to the Network tab at the top. Click refresh if necessary to view the network requests.
3. Follow the steps below for how to find each item using the dev panel.

**Tip:** You can filter request names by clicking the filter icon in the bar near the top. Then type in text to filter, and also click options on the right to filter by type such as `Fetch/XHR`.

<img width="344" height="89" alt="image" src="https://github.com/user-attachments/assets/2959c596-a6c5-466a-b286-eea7b19dc1f5" />


### Finding the Auth Token
1. With the dev tools open to the Network tab, via the dashboard site for your device, perform any action such as clicking the power toggle.
2. In the network tab you should see a couple requests at the bottom, such as `SetPowerMode`. Click on the one that has `xhr` in the `Type` column.
3. Another panel will open on the right. Look in the "Headers" tab, then under "Requeset Headers", look for the "Authorization" entry.
4. Copy the big long string next to the word `Bearer`. That string is your **Auth Token**
   - (Note: You don't need to include the word 'Bearer' when copying).

### Finding Your User ID and Login Token:
1. With the dev tools open to the Network tab, click the filter icon and filter for the text "account".
    - You should see one called something like `account?units.system=imperial&AQI=US&language=en`. Click that.
    - If you don't see an entry, refresh the dashboard page (make sure you're already logged in).
2. Another panel will open on the right, and go to the "Headers" tab. Near the top look for the `Request URL`
    - The full URL will look something like: `https://website-api.airvisual.com/v1/users/xxxxxxxxxxxxxxxxxxxxxx/account?units.system=imperial&AQI=US&language=en`
    - The `xxxxxxxxx` placeholder above is where your **User ID** will be, copy that part between the slashes.
4. In that same panel, scroll further down, and within the "Request Headers" section look for `X-Login-Token` (it may be at the very bottom)
    - Copy that value, that is your **Login Token**.
  

## Example Screenshot

<p align="center"><img width="766" height="419" alt="image" src="https://github.com/user-attachments/assets/986c909f-6d27-4b31-ae4f-b6d126040316" /></p>

# Extras

## Tools

- `gRPC Decode.html`: The cloud API sends and receives GRPC requests encoded as base64, so this browser based tool lets you paste in the payload and see the contents. Useful for API testing and debugging.
