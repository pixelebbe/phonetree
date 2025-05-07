# pixelebbe phone tree handler

This implements the phone tree that allows SIP users to automatically set pixels at pixelebbe events.

The expected behavior is:

1. User calls Eventphone Extension, the PyVoIP client picks up and plays welcome message
2. User inputs pixel coordinates and color in the format `#x#y#color*`. Any input before the first # is discarded.
3. The service validates the input and forwards the request to the pixelebbe server:
   - If input is invalid: play invalid message
   - If not the last attempt: also play try again message
   - If input is valid: play saving message, make API request
     - On success: play success message
     - On failure: play error message
4. Repeat from step 2 until valid input or max retries reached
5. Play goodbye message and hang up

## Prerequisites

- Python 3.6+
- EventPhone SIP Extension or Fritz!Box PBX for testing

## Quick Setup

The easiest way to set up the project is to use the automated setup script:

```bash
python setup.py
```

This will:

1. Create a Python virtual environment
2. Install all required dependencies
3. Create a config.py file from the example

After running the setup script:

1. Edit `config.py` with your SIP credentials and server settings
2. Activate the virtual environment and run the service

## Manual Installation

If you prefer to set up manually, follow these steps:

1. Create and activate a Python virtual environment:
   ```bash
   # Create virtual environment
   python -m venv venv

   # Activate on Linux/macOS
   source venv/bin/activate

   # Activate on Windows
   .\venv\Scripts\activate
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create your configuration file:
   ```bash
   cp example.config.py config.py
   ```
   Then edit `config.py` with your SIP credentials and server settings.

## Included Audio Files

The repository includes all necessary audio files (8kHz, mono, 16-bit WAV format):

- welcome.wav - Initial greeting
- input.wav - Prompt for pixel coordinates and color
- invalid.wav - Invalid input message
- tryagain.wav - Prompt to try input again
- saving.wav - Saving/processing message
- success.wav - Success message
- error.wav - Error message
- bye.wav - Goodbye message

## Running the Service

1. Make sure your virtual environment is activated:
   ```bash
   # On Linux/macOS
   source venv/bin/activate

   # On Windows
   .\venv\Scripts\activate
   ```

2. Start the phone tree service:
   ```bash
   python py_voip_client.py
   ```

The service will:

1. Register with your SIP provider using the credentials from `config.py`
2. Listen for incoming calls
3. Handle each call according to the phone tree logic
4. Log activity to the console

## API Integration

The service makes GET requests to the pixelebbe server in the format:

```http
GET {PIXELEBBE_URL}/pixel/{x}/{y}/{color}
```

Any 2xx response code is considered successful.

## Troubleshooting

1. Check the logs:
   - The service logs to the console by default
   - Look for SIP registration errors or connection issues

2. Common issues:
   - Wrong SIP credentials in config.py
   - Network/firewall blocking SIP traffic
   - Wrong server address or port
   - Virtual environment not activated (pip/python using system installation)
   - config.py not created or misconfigured
