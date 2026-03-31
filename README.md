# PDFMate+ – PDF Combiner & Toolkit v1.0.0

PDFMate+ is a professional desktop PDF utility designed to merge, edit, compress, and manage PDF documents and images in a fast, intuitive, and reliable environment.

The application is built for developers, office users, students, and productivity-focused professionals who require an all-in-one offline PDF processing tool.

PDFMate+ emphasizes usability, performance, and reliability while providing advanced features such as drag-and-drop file management, page-level editing, optional compression, threaded processing, and modern light/dark UI themes.

This edition focuses on batch merging, page editing, preview metadata, background processing, and responsive user experience.

------------------------------------------------------------
WINDOWS DOWNLOAD (EXE)
------------------------------------------------------------

Download the latest Windows executable from GitHub Releases:

https://github.com/rogers-cyber/PDFMatePlus/releases

- No Python installation required
- Portable standalone executable
- Ready-to-run on Windows
- Optimized for productivity workflows

------------------------------------------------------------
DISTRIBUTION
------------------------------------------------------------

PDFMate+ is a commercial desktop utility.

This repository/documentation may include:

- Production-ready Python source code
- Compiled desktop executables (Windows)
- Commercial licensing system
- Offline license activation

Python is not required when using the compiled executable version.

------------------------------------------------------------
FEATURES
------------------------------------------------------------

CORE CAPABILITIES

- 📄 Merge multiple PDFs into one document
- 🖼 Merge images (JPG, PNG, TIFF) into PDF
- 📂 Batch file processing
- 📁 Folder import support
- 🔀 Drag & drop file ordering
- 🧭 Manual reorder controls
- ✂ Page-level editor (rotate, delete, split)
- 🗜 Optional PDF compression (Ghostscript)
- 🎨 Light & Dark theme toggle
- 📊 Real-time progress tracking
- 📜 Live processing logs
- 🛑 Safe cancellation support

FILE MANAGEMENT

PDFMate+ provides flexible file management:

- Add individual files
- Add folders recursively
- Drag & drop support
- Remove selected items
- Clear full list
- Reorder items by drag
- Move up / move down buttons

These capabilities enable fast preparation of merge workflows.

PDF MERGING SYSTEM

PDFMate+ merges PDFs and images into a single document.

Features include:

- Sequential merge order
- Image-to-PDF conversion
- Memory-efficient processing
- Background threaded execution
- Error-safe processing

The merged output is saved to a user-defined location.

PAGE EDITOR

PDFMate+ includes a built-in page editor.

Capabilities:

- Rotate pages (+90 / -90)
- Delete selected pages
- Split selected pages into new PDF
- Save edited PDF
- Replace original item automatically

This allows quick corrections before merging.

COMPRESSION SYSTEM

Optional PDF compression is available using Ghostscript.

Compression features:

- Reduce PDF file size
- Maintain readability
- Configurable quality levels
- Automatic fallback if unavailable

Ghostscript is optional and only required for compression.

PERFORMANCE & UX

PDFMate+ is optimized for responsiveness.

Features include:

- Multi-threaded processing engine
- Non-blocking UI
- ASCII progress bar
- ETA calculation
- Real-time logging
- Drag & drop support
- Theme switching
- Responsive layout

The application remains smooth during heavy processing.

STABILITY & SAFETY

Robust error handling ensures safe operation.

Safety mechanisms include:

- Thread-safe UI updates
- Exception-safe file processing
- Temporary working directory
- Automatic cleanup
- Stop processing safely
- Missing file detection
- File size limits
- Maximum file count limits

These mechanisms prevent crashes and data loss.

------------------------------------------------------------
APPLICATION UI OVERVIEW
------------------------------------------------------------

TOP CONTROL BAR

Main actions:

- Add Files
- Clear List
- Toggle Theme
- About

ITEM LIST PANEL

Displays files to merge.

Features:

- Drag to reorder
- Scrollable list
- Remove selected item
- Move up / down controls
- Page editor access

PREVIEW PANEL

Displays selected file metadata.

Information shown:

- File name
- File type
- File path

OPTIONS PANEL

Processing options include:

- Compress output PDF (Ghostscript)

OUTPUT PANEL

- Output filename input
- Save dialog support
- Start processing
- Stop processing

PROGRESS PANEL

Displays:

- ASCII progress bar
- Percentage
- ETA
- Processed count
- Progress bar widget
- Real-time log output

------------------------------------------------------------
INSTALLATION (SOURCE CODE)
------------------------------------------------------------

1. Clone the repository:

git clone https://github.com/rogers-cyber/PDFMatePlus.git

Navigate to the project directory:

cd PDFMatePlus

2. Install required dependencies:

pip install PyPDF2 pypdf pillow img2pdf tkinterdnd2 pyperclip cairosvg

Tkinter is included with standard Python installations.

3. Run the application:

python PDFMatePlus.py

------------------------------------------------------------
OPTIONAL DEPENDENCIES
------------------------------------------------------------

Ghostscript (for compression):

https://ghostscript.com

Ensure "gs" is available in system PATH.

------------------------------------------------------------
BUILD WINDOWS EXECUTABLE
------------------------------------------------------------

You can create a standalone Windows executable using PyInstaller.

Install PyInstaller:

pip install pyinstaller

Build the application:

pyinstaller --onefile --windowed --name "PDFMatePlus" --icon=logo.ico PDFMatePlus.py

The compiled executable will appear in:

dist/PDFMatePlus.exe

------------------------------------------------------------
USAGE GUIDE
------------------------------------------------------------

1. Add Files

Click:

Add Files  

or drag and drop PDFs/images.

2. Reorder Files

Drag items in the list  
or use Move Up / Move Down.

3. Edit Pages (Optional)

Select a PDF  
Click:

Split / Edit Pages  

Rotate, delete, or split pages.

4. Configure Options

Enable compression if desired.

5. Set Output File

Enter output filename  
or choose save location.

6. Merge Files

Click:

Merge/Process  

Monitor progress and logs.

7. Stop Processing

Click:

Stop  

Safely cancels operation.

------------------------------------------------------------
LOGGING & ERROR HANDLING
------------------------------------------------------------

PDFMate+ maintains real-time logs.

- All operations shown in log panel
- Errors displayed without crashing
- Safe exception handling
- Thread-safe logging
- Processing continues when possible

------------------------------------------------------------
REPOSITORY STRUCTURE
------------------------------------------------------------

PDFMatePlus/

├── PDFMatePlus.py  
├── splash.png  
├── logo.ico  
├── README.md  
├── LICENSE  

Generated at runtime:

├── ~/.pdfmate/settings.ini  
├── ~/.pdfmate/license.dat  

------------------------------------------------------------
DEPENDENCIES
------------------------------------------------------------

Python 3.9+

Libraries used:

- PyPDF2
- pypdf
- pillow
- img2pdf
- tkinterdnd2
- pyperclip
- cairosvg
- tkinter
- threading
- tempfile
- configparser
- logging
- subprocess
- hashlib
- queue
- datetime
- os
- sys
- time
- shutil

------------------------------------------------------------
INTENDED USE
------------------------------------------------------------

PDFMate+ is ideal for:

- Merging PDF documents
- Combining scanned images
- Preparing reports
- Document packaging
- Office workflows
- Developer utilities
- Batch PDF automation
- File size reduction
- Page-level PDF editing

The tool is optimized for offline productivity workflows.

------------------------------------------------------------
ABOUT
------------------------------------------------------------

PDFMate+ is developed by Mate Technologies, focused on building professional offline productivity tools for Windows users.

Website:

https://matetools.gumroad.com

© 2026 Mate Technologies  
All rights reserved.

------------------------------------------------------------
LICENSE
------------------------------------------------------------

PDFMate+ is commercial software.

License terms:

- Personal and commercial use allowed
- Redistribution not permitted
- Repackaging or resale prohibited
- Modification for private use allowed
- Standalone executable permitted
- License activation required

For commercial licensing or enterprise deployment, contact the developer.