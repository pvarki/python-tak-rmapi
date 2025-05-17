
Frontend instructions are pulled from https://github.com/pvarki/rune-tak-metadata/releases/latest/download/rune.json and is stored to /opt/templates/tak.json where it is served to frontend through rasenmaeher-api.


The Rune tool and rune.json is described more in detail here https://github.com/hyperifyio/rune


The tak-rmapi adds TAK zip packages to the provided json as extra "Asset" objects.


There is folder for static files (tak_www_static) that can be accessed through products nginx proxy mtls.tak.[domain_name]:4626/static/x. For example https://mtls.tak.localmaeher.dev.pvarki.fi:4626/static/test_image.png
