# FastFromVod
creating a Fast channel using Vod Sources

## create copies from a template
for i in $(seq -w 1 31) ; do cat SBS6\ Classics-2023-05-31.xml | sed -E "s/2023-05-31/2023-06-$i/g" > sbs6_202306$i.xml ; done

## try to create a schedule by parsing playlists
get_config_from_playlist.py -i input/sbs6_202307* -t 2023-07-19 

use -f to force creation even if some of the sources aren't available
