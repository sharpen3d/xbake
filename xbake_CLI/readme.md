# xBake CLI

Utilize xBake from command line, allowing for batched operation and external software integration.

## Requirements

- Blender 4.2 or later
- Download xbakeCLI.blend and run_xbake.py from this repo -- or clone this repo to have local access to these files
- xBake (extension installation) is *not required* to run the command line interface


### **Add Blender to PATH**

1. **Locate Blender's Executable**:
    - On **Windows**: Typically found in `C:\Program Files\Blender Foundation\Blender <version>\blender.exe`.
    - On **Mac**: Use `/Applications/Blender.app/Contents/MacOS/Blender`.
    - On **Linux**: It's usually `/usr/bin/blender` or wherever you installed Blender.
2. **Add to PATH**:
    - **Windows**:
        1. Search for "Environment Variables" in the Start Menu.
        2. Click "Edit the system environment variables."
        3. In the "System Properties" window, click "Environment Variables."
        4. Under "System variables," find and edit the `Path` variable.
        5. Add the directory containing `blender.exe` (e.g., `C:\Program Files\Blender Foundation\Blender <version>`).
    - **Mac/Linux**:
    Add Blender's executable path to your shell configuration file (e.g., `~/.bashrc` or `~/.zshrc`):Replace `/path/to/blender` with the actual path to Blender.
        
        ```bash
        export PATH="/path/to/blender:$PATH"
        ```
        
3. **Verify PATH**:
Restart your terminal or system and run:
    
    ```bash
    blender --version
    ```
    
    If it prints Blender's version, the setup is correct.
    

## First-Use Setup

**Open the xBake CLI template file**

- Find `xBakeCLI.blend` and open it.
- When prompted, check Always Allow Execution
- You can now close this file

<aside>
💡

- This step initiated automatic execution of required embedded python when running from command line - you only need to do this once
</aside>

## Command-Line Usage

### Example Command

```bash
blender /your/system/path/to/xbakeCLI.blend --background --python /your/system/path/to/run_xbake.py -- --lowpoly /path/to/lowpoly.fbx --highpoly /path/to/highpoly.fbx --extrusion 0.4 --usenormal True --normal_format OPENGL --resolution 4096
```

### Explanation

- `-background`: Runs Blender in background mode.
- `-python run_xbake.py`: Specifies the Python script to execute - always point this to the full system path to run_xbake.py
- `-`: Separates Blender arguments from script arguments.
- Required arguments:
    - `-lowpoly`: Path to the low-poly FBX file.
    - `-highpoly`: Path to the high-poly FBX file.
- Optional Arguments
    - `-extrusion`: Extrusion value for baking (default `0.5`).
    - `-normal_format`: Specify normal map format (`OPENGL` or `DIRECTX`).
    - `-resolution`: Output resolution (default `2048`).
    - `-usemayaorientation`: Uses `+Y up and +Z forward` rather than `+Z up and +Y forward` for position and normal orientation
- Optional Arguments Continued (bake types) *all `True` by default
    - `-usenormal`: Enable/disable normal map baking (default `True`).
    - `-useao`: Enable/disable ambient occlusion map baking (default `True`).
    - `-usecurvature`: Enable/disable curvature map baking (default `True`).
    - `-useposition`: Enable/disable world space position (normalized) map baking (default `True`).
    - `-usecworldspacenormal`: Enable/disable world space normal (normalized) map baking (default `True`).

### Example Command Called From System Python Script

```python
import subprocess

# Command details
blender_path = "/path/to/blender"
blend_file = "/path/to/yourfile.blend"
script_file = "/path/to/run_xbake.py"
lowpoly_path = "/path/to/lowpoly.fbx"
highpoly_path = "/path/to/highpoly.fbx"

# Command construction
cmd = [
    blender_path,
    blend_file,
    "--background",
    "--python", script_file,
    "--",
    "--lowpoly", lowpoly_path,
    "--highpoly", highpoly_path,
    "--resolution", "4096"
]

# Execute command
subprocess.run(cmd)
```

## Saved Maps

Baked maps will appear in a folder `baked_maps` in the directory of your low-poly fbx.

Naming of baked maps will follow the convention of your low-poly fbx, however, if low poly and high poly fbx share a naming prefix (i.e. `mymodel_low`, `mymodel_high`) - baked maps will be named after the prefix (i.e. `mymodel`)

Blender automatically cleans up and exits after baking maps via CLI, not storing any temporary data.

## Debugging

The simplest way to debug errors using xBake for CLI is to simply manually perform the baking via extension rather than command line.

Some common errors related to command line specifically will likely stem from improper fbx import - since this is ‘blind’ - unit conversion may make files from external software much larger or smaller than default baking values account for, ideal scale for baking is a bounding box between 1 and 10 blender-units large. 

This is a new process and all features of the extension have not been added, feel free to request xBake features for CLI integration on GitHub by reporting an issue.
