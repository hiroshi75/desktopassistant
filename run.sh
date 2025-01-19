#!/bin/bash

# Set PYTHONPATH to include the project root directory
export PYTHONPATH="$PWD"

# Platform-specific setup
case "$(uname -s)" in
    Linux*)
        # X11 display setup for Linux
        if [ -z "$DISPLAY" ]; then
            if [ -x "$(command -v xhost)" ]; then
                export DISPLAY=":0"
                echo "Setting DISPLAY to :0"
            else
                echo "Warning: X11 environment not detected"
            fi
        fi
        
        # Check for Qt dependencies
        if ! python3 -c "import PyQt5" 2>/dev/null; then
            echo "Installing PyQt5..."
            pip3 install PyQt5
        fi
        ;;
    Darwin*)
        echo "Running on macOS"
        ;;
    *)
        echo "Unknown platform: $(uname -s)"
        ;;
esac

# Ensure script exits cleanly
cleanup() {
    echo "Cleaning up..."
    pkill -f "python3 desktopassistant/main.py"
    exit 0
}

# Set up trap for cleanup on script exit
trap cleanup EXIT INT TERM

# Run the desktop assistant application
python3 desktopassistant/main.py

# Wait for all background processes and ensure clean exit
wait
exit 0
