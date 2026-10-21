# Sourced by start.sh before Jellyfin opens its configuration. Same package UID.
hwa_device() {
    case "$1" in /dev/dri/renderD[0-9][0-9][0-9]) ;; *) return 1;; esac
    minor=${1#/dev/dri/renderD}
    [ "$minor" -ge 128 ] && [ "$minor" -le 191 ]
}

hwa_write() {
    hwa_state=$1; hwa_backend=$2; hwa_path=$3
    case "$hwa_backend" in vaapi) hwa_device "$hwa_path" || return 1;; none) ;; *) return 1;; esac
    hwa_config="$hwa_state/config/config/encoding.xml"
    mkdir -p "$hwa_state/config/config"
    if [ -L "$hwa_config" ]; then return 1; fi
    if [ -f "$hwa_config" ]; then
        # Change native serialized fields only; retain all unrelated user settings.
        # If a future upstream format differs, leave it untouched and fail safely.
        grep -q '</EncodingOptions>' "$hwa_config" || return 1
        sed "s|<HardwareAccelerationType>[^<]*</HardwareAccelerationType>|<HardwareAccelerationType>$hwa_backend</HardwareAccelerationType>|g" "$hwa_config" > "$hwa_config.pending"
        if ! grep -q '<HardwareAccelerationType>' "$hwa_config.pending"; then
            sed "s|</EncodingOptions>|<HardwareAccelerationType>$hwa_backend</HardwareAccelerationType></EncodingOptions>|" "$hwa_config.pending" > "$hwa_config.pending2"
            mv "$hwa_config.pending2" "$hwa_config.pending"
        fi
        if [ "$hwa_backend" = vaapi ]; then
            sed "s|<VaapiDevice>[^<]*</VaapiDevice>|<VaapiDevice>$hwa_path</VaapiDevice>|g; s|<EnableHardwareEncoding>[^<]*</EnableHardwareEncoding>|<EnableHardwareEncoding>true</EnableHardwareEncoding>|g" "$hwa_config.pending" > "$hwa_config.pending2"
            mv "$hwa_config.pending2" "$hwa_config.pending"
            if ! grep -q '<VaapiDevice>' "$hwa_config.pending"; then
                sed "s|</EncodingOptions>|<VaapiDevice>$hwa_path</VaapiDevice></EncodingOptions>|" "$hwa_config.pending" > "$hwa_config.pending2"
                mv "$hwa_config.pending2" "$hwa_config.pending"
            fi
        fi
    elif [ "$hwa_backend" = vaapi ]; then
        printf '<?xml version="1.0"?><EncodingOptions><HardwareAccelerationType>vaapi</HardwareAccelerationType><VaapiDevice>%s</VaapiDevice><EnableHardwareEncoding>true</EnableHardwareEncoding><HardwareDecodingCodecs><string>h264</string></HardwareDecodingCodecs></EncodingOptions>\n' "$hwa_path" > "$hwa_config.pending"
    else
        return 0
    fi
    chmod 600 "$hwa_config.pending"
    mv "$hwa_config.pending" "$hwa_config"
}

hwa_setup() {
    hwa_state=$1
    hwa_path=${SYNOPKGLAND_GPU_DEVICE:-}
    if [ "${SYNOPKGLAND_GPU_STATUS:-software}" = available ] && hwa_device "$hwa_path" && [ -c "$hwa_path" ] && [ -r "$hwa_path" ] && [ -w "$hwa_path" ] &&
        timeout 15 /usr/lib/jellyfin-ffmpeg/ffmpeg -hide_banner -loglevel error -init_hw_device "vaapi=va:$hwa_path" -filter_hw_device va -f lavfi -i color=s=64x64:r=1 -vf format=nv12,hwupload -frames:v 1 -c:v h264_vaapi -f null - >/dev/null 2>&1; then
        if [ ! -f "$hwa_state/hwa.initialized" ]; then
            hwa_write "$hwa_state" vaapi "$hwa_path" || return 1
            : > "$hwa_state/hwa.initialized"
        fi
        printf '%s\n' 'GPU render device ready; native encoding settings retained.'
    else
        hwa_write "$hwa_state" none '' || return 1
        rm -f "$hwa_state/hwa.initialized"
        printf '%s\n' 'Hardware acceleration unavailable; using software transcoding.'
    fi
}
