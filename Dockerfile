# Použijeme oficiální odlehčený obraz Pythonu
FROM python:3.11-slim

# Vytvoříme a nastavíme pracovní složku uvnitř kontejneru
WORKDIR /app

# Zkopírujeme soubor se závislostmi a nainstalujeme je
# (Ujisti se, že máš v repozitáři aktuální requirements.txt)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Zkopírujeme veškerý zbytek tvého kódu
COPY . .

# Kontejner bude naslouchat na portu 8000
EXPOSE 8000

# Příkaz pro spuštění FastAPI serveru tak, aby byl přístupný zvenku (0.0.0.0)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]