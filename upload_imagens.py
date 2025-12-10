import requests

# URL do seu endpoint Flask
URL_UPLOAD = "http://54.210.38.182:5000/revistas/upload"

# Quantas imagens você quer enviar
NUM_IMAGENS = 5

for i in range(NUM_IMAGENS):
    # Pegar uma imagem aleatória (200x200)
    response = requests.get("https://picsum.photos/200/200")
    
    if response.status_code == 200:
        # Cria um arquivo temporário na memória
        files = {'file': ('imagem_{}.jpg'.format(i), response.content, 'image/jpeg')}
        
        # Envia para o seu endpoint
        r = requests.post(URL_UPLOAD, files=files)
        
        if r.status_code == 200:
            print(f"Upload {i+1}: Sucesso! URL -> {r.json().get('url')}")
        else:
            print(f"Upload {i+1}: Falhou. Status {r.status_code}")
    else:
        print(f"Erro ao baixar imagem {i+1}")
