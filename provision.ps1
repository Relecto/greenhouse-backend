param (
    [string]$port = "COM3"
)

$ErrorActionPreference = "Stop"

echo "Ensuring the board is connected..."

python pyboard.py '--device' "$port" '-c' 'import hw_info; print(hw_info.NAME)'
python pyboard.py '--device' "$port" '-c' 'import hw_info; print(hw_info.SERIAL)'

echo "Transfering files..."

python pyboard.py --device $port -f mkdir public 
python pyboard.py --device $port -f cp public/bundle.js :public/bundle.js 
python pyboard.py --device $port -f cp public/index.html :public/index.html 

python pyboard.py --device $port -f cp main.py :main.py 
python pyboard.py --device $port -f cp boot.py :boot.py 
python pyboard.py --device $port -f cp helpers.py :helpers.py 

echo "Done. Quiting..."