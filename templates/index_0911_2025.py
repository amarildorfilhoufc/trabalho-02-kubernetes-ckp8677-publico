<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <title>Sistema de Periódicos</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
    <div class="container py-5">
        <h1 class="text-center mb-4">📚 Sistema de Periódicos</h1>

        <div class="text-center mb-4">
            <button class="btn btn-primary me-2" onclick="carregarRevistas()">Revistas</button>
            <button class="btn btn-success" onclick="carregarArtigos()">Artigos</button>
        </div>

        <div id="conteudo" class="card p-4 shadow-sm bg-white"></div>
    </div>

    <script>
        async function carregarRevistas() {
            const resp = await fetch('/revistas');
            const dados = await resp.json();
            let html = "<h3>Revistas</h3><ul class='list-group'>";
            dados.forEach(r => {
                html += `<li class='list-group-item'>
                    <b>${r.nome}</b> (${r.area}) - ISSN: ${r.issn}
                    <button class='btn btn-danger btn-sm float-end' onclick='excluirRevista(${r.id})'>Excluir</button>
                </li>`;
            });
            html += "</ul>";
            document.getElementById('conteudo').innerHTML = html;
        }

        async function carregarArtigos() {
            const resp = await fetch('/artigos');
            const dados = await resp.json();
            let html = "<h3>Artigos</h3><ul class='list-group'>";
            dados.forEach(a => {
                html += `<li class='list-group-item'>
                    <b>${a.titulo}</b> - ${a.autor} (Revista ID: ${a.revista_id})
                    <button class='btn btn-danger btn-sm float-end' onclick='excluirArtigo(${a.id})'>Excluir</button>
                </li>`;
            });
            html += "</ul>";
            document.getElementById('conteudo').innerHTML = html;
        }

        async function excluirRevista(id) {
            await fetch(`/revistas/${id}`, { method: 'DELETE' });
            carregarRevistas();
        }

        async function excluirArtigo(id) {
            await fetch(`/artigos/${id}`, { method: 'DELETE' });
            carregarArtigos();
        }
    </script>
</body>
</html>
