param (
    [string]$port = "COM3",
)

$ErrorActionPreference = "Stop"

echo "Ensuring the board is connected..."

pyboard.py --device $port -c 'import hw_info; print(f"{hw_info.NAME} #{hw_info.SERIAL}")'

echo "Transfering files..."

pyboard.py --device $port -f mkdir public 
pyboard.py --device $port -f cp public/bundle.js :public/bundle.js 
pyboard.py --device $port -f cp public/index.html :public/index.html 

pyboard.py --device $port -f cp main.py :main.py 
pyboard.py --device $port -f cp boot.py :boot.py 
pyboard.py --device $port -f cp helpers.py :helpers.py 

echo "Done. Quiting..."