\# Graceful IP-Range Scanner



A fast, \*\*graceful\*\* IP-range scanner in Python that:



\- Reads IP ranges from a file (e.g., Angry IP Scanner export)

\- Pings selected IPs in parallel using threads

\- Supports three scanning modes: `edge\_only`, `sample`, and `full`

\- Handles `Ctrl+C` (KeyboardInterrupt) and still \*\*saves partial results\*\*

\- Writes live IPs to both `.txt` and `.csv` output files



---



\## Features



\- ✅ Reads ranges from a simple text/TSV file  

\- ✅ Cross-platform ping support (Windows \& Linux)  

\- ✅ Threaded scanning using `ThreadPoolExecutor`  

\- ✅ Configurable:

&nbsp; - Scan mode (`edge\_only`, `sample`, `full`)

&nbsp; - Sampling step (how densely to probe in `sample` mode)

&nbsp; - Number of worker threads

&nbsp; - Ping timeout

\- ✅ Saves results even when you stop with `Ctrl+C`



---



\## How it works



1\. \*\*Input file format\*\*



The script expects a text file where each line contains:



```text

<start\_ip> <end\_ip>



