#!/bin/bash

# =========================================================
# CUDA Version Management Configuration (Managed by .cuda_switcher.sh)
# =========================================================

# Define CUDA configurations. Each entry is a colon-separated string:
# "INDEX:VERSION_STRING:CUDA_ROOT_PATH"
#
# INDEX: A number (0, 1, 2...) you'll use to select this configuration.
# VERSION_STRING: Just for display, e.g., "12.6", "12.9".
# CUDA_ROOT_PATH: The actual installation path of the CUDA toolkit, e.g., /usr/local/cuda-12.6.
#
# Note: cufile.json will be accessed via /usr/local/cuda/gds/cufile.json automatically
#       once /usr/local/cuda points to the correct version.
#
# Important: Ensure these paths actually exist on your system!
declare -a CUDA_CONFIGS=(
  "0:12.6:/usr/local/cuda-12.6"
  "1:12.9:/usr/local/cuda-12.9"
)

# =========================================================
# End CUDA Configuration
# =========================================================


# =========================================================
# Functions for CUDA Version Management
# =========================================================

# Function to register all defined CUDA versions with update-alternatives
# Run this once after defining CUDA_CONFIGS and after installing new CUDA versions.
register_cuda_alternatives() {
    echo "--- Registering CUDA alternatives ---"
    local config_entry index version cuda_root_path priority

    for config_entry in "${CUDA_CONFIGS[@]}"; do
        IFS=':' read -r index version cuda_root_path <<< "$config_entry"
        # Generate a priority based on version (e.g., 12.6 -> 126, 12.9 -> 129)
        priority=$(echo "$version" | tr -d '.' | cut -c 1-3)

        # 1. Register 'cuda' alternative (/usr/local/cuda)
        if [ -d "$cuda_root_path" ]; then
            sudo update-alternatives --install /usr/local/cuda cuda "$cuda_root_path" "$priority"
            echo "  Registered 'cuda' for v$version: $cuda_root_path (Priority: $priority)"
        else
            echo "  Warning: CUDA root path '$cuda_root_path' for v$version does not exist. Skipping 'cuda' registration."
        fi

	# 2. Register 'cuda-12' alternative (/usr/local/cuda-12)
        #    This alternative is typically only registered for CUDA 12.x versions.
        if [[ "$version" =~ ^12\..* ]]; then # 检查版本字符串是否以 "12." 开头
            if [ -d "$cuda_root_path" ]; then
                sudo update-alternatives --install /usr/local/cuda-12 cuda-12 "$cuda_root_path" "$priority"
                echo "  Registered 'cuda-12' for v$version: $cuda_root_path (Priority: $priority)"
            else
                echo "  Warning: CUDA root path '$cuda_root_path' for v$version does not exist. Skipping 'cuda-12' registration."
            fi
        else
            echo "  Note: Skipping 'cuda-12' registration for non-12.x version v$version."
        fi
    done
    echo "--- Registration complete ---"
}


# Function to switch CUDA, cuda-12 alternatives
# Usage: switch_cuda <selection_index>
# Example: switch_cuda 0 (to activate CUDA XX.X)
switch_cuda() {
    local selected_index="$1"
    local found_config=false
    local config_entry index version cuda_root_path

    if [[ -z "$selected_index" ]]; then
        echo "Usage: switch_cuda <selection_index>"
        echo "Available CUDA configurations:"
        for config_entry in "${CUDA_CONFIGS[@]}"; do
            IFS=':' read -r index version <<< "$config_entry"
            echo "  $index: CUDA $version"
        done
        return 1
    fi

    echo "--- Attempting to switch CUDA configuration to index: $selected_index ---"

    for config_entry in "${CUDA_CONFIGS[@]}"; do
        IFS=':' read -r index version cuda_root_path <<< "$config_entry"

        if [[ "$index" == "$selected_index" ]]; then
            found_config=true
            echo "Selected configuration: CUDA $version"

            # 1. Set 'cuda' alternative
            if [ -d "$cuda_root_path" ]; then
                sudo update-alternatives --set cuda "$cuda_root_path"
                echo "  '/usr/local/cuda' is now linked to: $cuda_root_path"
            else
                echo "  Error: CUDA root path '$cuda_root_path' does not exist. Cannot set 'cuda'."
                return 1
            fi

            # 2. Set 'cuda-12' alternative
            # Since all your versions are 12.x, this will always be set.
            if [ -d "$cuda_root_path" ]; then
                sudo update-alternatives --set cuda-12 "$cuda_root_path"
                echo "  '/usr/local/cuda-12' is now linked to: $cuda_root_path"
            else
                echo "  Error: CUDA root path '$cuda_root_path' does not exist. Cannot set 'cuda-12'."
                return 1
            fi

            echo "--- CUDA configuration switched successfully ---"
            echo "Please log out and log back in, or restart your terminal/system for changes to take full effect on all applications."
            echo "You can verify with: nvcc --version, readlink -f /usr/local/cuda, and readlink -f /usr/local/cuda-12"
            return 0
        fi
    done

    if ! "$found_config"; then
        echo "Error: Invalid selection number '$selected_index'."
        echo "Available CUDA configurations:"
        for config_entry in "${CUDA_CONFIGS[@]}"; do
            IFS=':' read -r index version <<< "$config_entry"
            echo "  $index: CUDA $version"
        done
        return 1
    fi
}

# Add CUDA bin and lib64 to PATH and LD_LIBRARY_PATH
# This ensures that /usr/local/cuda (the current active version) is found.
export PATH="/usr/local/cuda/bin:${PATH}"
export LD_LIBRARY_PATH="/usr/local/cuda/lib64:${LD_LIBRARY_PATH}"
