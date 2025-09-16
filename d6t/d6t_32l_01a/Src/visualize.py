import serial
import re
import numpy as np
import matplotlib.pyplot as plt
import time

# Configuration
SERIAL_PORT = 'COM3'  # Change to your serial port (e.g., '/dev/ttyUSB0' on Linux/Mac)
BAUD_RATE = 115200
TIMEOUT = 1
PARSE_TIMEOUT = 10  # Seconds to wait for valid data

def parse_uart_data(ser):
    """
    Reads from serial port and parses the thermal data.
    Returns ptat, avg_temp, and 32x32 pixel grid as numpy array.
    """
    ptat = None
    avg_temp = None
    pixels = np.zeros((32, 32))
    buffer = ''
    start_time = time.time()
    
    while time.time() - start_time < PARSE_TIMEOUT:
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        if not line:
            continue
        
        buffer += line + '\n'
        
        # Parse PTAT line
        ptat_match = re.search(r'PTAT: (-?\d+\.\d+) C, PEC: 0x[0-9A-Fa-f]{2}', buffer)
        if ptat_match:
            ptat = float(ptat_match.group(1))
        
        # Parse Avg line
        avg_match = re.search(r'Avg Pixel Temp: (-?\d+\.\d+) C', buffer)
        if avg_match:
            avg_temp = float(avg_match.group(1))
        
        # Parse pixel grid: 32 lines of 32 space-separated floats
        if avg_temp is not None and ptat is not None:
            grid_lines = re.findall(r'^(-?\d+\.\d+(?: -?\d+\.\d+){31})$', buffer, re.MULTILINE)
            if len(grid_lines) >= 32:
                try:
                    for row in range(32):
                        row_data = list(map(float, grid_lines[row].split()))
                        if len(row_data) == 32:
                            pixels[row, :] = row_data
                    return ptat, avg_temp, pixels
                except ValueError as e:
                    print(f"Parsing error: {e}")
                    buffer = ''  # Reset on error
                    continue
        
        # Reset buffer if too large
        if len(buffer) > 10000:
            print("Buffer overflow, resetting...")
            buffer = ''
    
    print("Parse timeout: No valid data received.")
    return None, None, None

def visualize_heatmap(ptat, avg_temp, pixels, fig, ax, im=None):
    """
    Updates or creates a heatmap in the same window using matplotlib.
    Returns the updated image object.
    """
    if im is None:
        im = ax.imshow(pixels, cmap='hot', interpolation='nearest', aspect='equal')
        fig.colorbar(im, label='Temperature (°C)')
        ax.set_title(f'Thermal Heatmap\nPTAT: {ptat:.1f}°C | Avg: {avg_temp:.1f}°C')
        ax.set_xlabel('Column')
        ax.set_ylabel('Row')
    else:
        im.set_data(pixels)
        ax.set_title(f'Thermal Heatmap\nPTAT: {ptat:.1f}°C | Avg: {avg_temp:.1f}°C')
        im.set_clim(vmin=np.min(pixels), vmax=np.max(pixels))
    fig.canvas.draw()
    fig.canvas.flush_events()
    return im

# Main loop
try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=TIMEOUT)
    print(f"Connected to {SERIAL_PORT}. Waiting for data...")
    
    plt.ion()  # Enable interactive mode
    fig, ax = plt.subplots(figsize=(10, 8))
    im = None
    
    while True:
        ptat, avg_temp, pixels = parse_uart_data(ser)
        if pixels is not None:
            print(f"Received data - PTAT: {ptat:.1f}°C, Avg: {avg_temp:.1f}°C")
            im = visualize_heatmap(ptat, avg_temp, pixels, fig, ax, im)
        else:
            print("No valid data parsed.")
        time.sleep(0.1)  # Small delay to prevent CPU overload
        
except KeyboardInterrupt:
    print("Stopping...")
except serial.SerialException as e:
    print(f"Serial error: {e}")
finally:
    if 'ser' in locals():
        ser.close()
    plt.ioff()
    plt.close('all')