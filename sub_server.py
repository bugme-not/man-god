{
  "log": {
    "loglevel": "none"
  },
  "dns": {
    "servers": [
      {
        "address": "https://1.1.1.1/dns-query",
        "skipFallback": true
      },
      "8.8.8.8"
    ],
    "queryStrategy": "UseIPv4",
    "cacheStrategy": "Enabled"
  },
  "inbounds": [
    {
      "port": 10085,
      "listen": "127.0.0.1",
      "protocol": "vless",
      "settings": {
        "clients": [
          {
            "id": "cxlvin777",
            "level": 0
          }
        ],
        "decryption": "none"
      },
      "streamSettings": {
        "network": "ws",
        "sockopt": {
          "tcpNoDelay": true,
          "tcpKeepAliveInterval": 15,
          "mark": 0
        },
        "wsSettings": {
          "path": "/CxlvinVlWS",
          "maxHeaderBytes": 2048
        }
      }
    }
  ],
  "outbounds": [
    {
      "protocol": "freedom",
      "tag": "direct",
      "settings": {
        "domainStrategy": "UseIP",
        "userLevel": 0
      },
      "streamSettings": {
        "sockopt": {
          "tcpNoDelay": true,
          "tcpKeepAliveInterval": 15,
          "domainStrategy": "UseIP"
        }
      }
    },
    {
      "protocol": "blackhole",
      "tag": "blocked",
      "settings": {
        "response": {
          "type": "none"
        }
      }
    }
  ],
  "routing": {
    "domainStrategy": "IPIfNonMatch",
    "rules": [
      {
        "type": "field",
        "ip": [
          "geoip:private"
        ],
        "outboundTag": "blocked"
      }
    ]
  }
}
