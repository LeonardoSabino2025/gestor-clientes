# Guia de Deploy — Gestor de Clientes (Streamlit + Docker)

Este guia assume que você sabe o básico de terminal, mas não é especialista
em Linux/DevOps. Vamos do zero até o app rodando no navegador.

Estrutura de arquivos que você deve ter recebido:

```
gestor-clientes/
├── app.py
├── requirements.txt
├── Dockerfile
├── .dockerignore
├── .gitignore
└── .streamlit/
    └── config.toml
```

---

## PARTE 1 — Repositório Git privado (na sua máquina local)

### 1.1. Criar o repositório privado no GitHub (ou GitLab/Bitbucket)

1. Acesse https://github.com/new
2. Dê um nome ao repositório, ex: `gestor-clientes`
3. Marque a opção **Private** (privado)
4. NÃO marque "Add a README" (para não dar conflito com o que já temos)
5. Clique em **Create repository**

O GitHub vai te mostrar uma URL parecida com:
```
https://github.com/SEU_USUARIO/gestor-clientes.git
```

### 1.2. Subir o código local para o repositório

No terminal, dentro da pasta `gestor-clientes/`:

```bash
cd gestor-clientes
git init
git add .
git commit -m "Primeiro commit: app de extração de telefones"
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/gestor-clientes.git
git push -u origin main
```

Se o Git pedir usuário/senha e recusar (o GitHub não aceita mais senha
comum), você vai precisar de um **Personal Access Token (PAT)** — veja a
Parte 3.3 abaixo, o processo é o mesmo tanto para o seu PC quanto para o
servidor.

---

## PARTE 2 — Preparar o servidor privado (VPS / NAS / servidor Linux)

### 2.1. Acessar o servidor via SSH

No seu terminal local:

```bash
ssh usuario@IP_DO_SERVIDOR
```

Exemplo:
```bash
ssh root@203.0.113.10
```

Se for a primeira vez, ele vai perguntar se confia no host — digite `yes`.

### 2.2. Instalar o Docker no servidor

Ainda dentro da sessão SSH (ou seja, já conectado no servidor), rode o
script oficial de instalação do Docker:

```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
```

Depois, adicione seu usuário ao grupo docker (para não precisar de `sudo`
em todo comando):

```bash
sudo usermod -aG docker $USER
```

**Importante:** saia do SSH e reconecte para que essa permissão passe a
valer:

```bash
exit
ssh usuario@IP_DO_SERVIDOR
```

Teste se o Docker está funcionando:

```bash
docker --version
docker run hello-world
```

Se aparecer uma mensagem de boas-vindas do Docker, está tudo certo.

---

## PARTE 3 — Clonar o repositório privado dentro do servidor

Como o repositório é privado, o servidor precisa se autenticar. Existem
duas formas — escolha uma:

### Opção A — Chave SSH (recomendada, mais segura, não expira)

1. No servidor, gere uma chave SSH (se ainda não tiver uma):
   ```bash
   ssh-keygen -t ed25519 -C "servidor-gestor-clientes"
   ```
   Aperte Enter em todas as perguntas (sem senha na chave, para
   simplificar automações).

2. Mostre a chave pública gerada:
   ```bash
   cat ~/.ssh/id_ed25519.pub
   ```
   Copie o conteúdo exibido (começa com `ssh-ed25519 ...`).

3. No GitHub: vá em **Settings → SSH and GPG keys → New SSH key**, cole a
   chave pública copiada e salve.

4. Agora clone usando a URL SSH (não a HTTPS):
   ```bash
   git clone git@github.com:SEU_USUARIO/gestor-clientes.git
   ```

### Opção B — Personal Access Token (PAT) (mais simples, porém expira)

1. No GitHub: vá em **Settings → Developer settings → Personal access
   tokens → Tokens (classic) → Generate new token**.
2. Marque o escopo `repo` (acesso a repositórios privados).
3. Copie o token gerado (ele só aparece uma vez).
4. No servidor, clone assim:
   ```bash
   git clone https://SEU_USUARIO:SEU_TOKEN@github.com/SEU_USUARIO/gestor-clientes.git
   ```
   (Substitua `SEU_USUARIO` e `SEU_TOKEN` pelos seus dados reais.)

Depois de clonado, entre na pasta:

```bash
cd gestor-clientes
```

---

## PARTE 4 — Build e execução do container Docker

### 4.1. Construir a imagem Docker

Dentro da pasta do projeto, no servidor:

```bash
docker build -t gestor-clientes:latest .
```

Isso vai ler o `Dockerfile`, instalar as dependências do
`requirements.txt` e empacotar o `app.py` dentro da imagem.

### 4.2. Rodar o container em background

```bash
docker run -d \
  --name gestor-clientes \
  --restart unless-stopped \
  -p 8501:8501 \
  gestor-clientes:latest
```

Explicando cada parte do comando:
- `-d` → roda em background (detached), não trava seu terminal
- `--name gestor-clientes` → dá um nome fácil de identificar ao container
- `--restart unless-stopped` → se o servidor reiniciar, o container sobe
  sozinho de novo
- `-p 8501:8501` → mapeia a porta 8501 do servidor para a porta 8501 do
  container (porta padrão do Streamlit)

### 4.3. Verificar se está rodando

```bash
docker ps
```

Você deve ver o container `gestor-clientes` com status `Up`.

Para ver os logs (útil se algo der errado):

```bash
docker logs -f gestor-clientes
```

(Aperte `Ctrl + C` para sair do modo de acompanhamento de logs.)

---

## PARTE 5 — Acessar o app pelo navegador

### 5.1. Via IP do servidor

Abra o navegador e acesse:

```
http://IP_DO_SERVIDOR:8501
```

Exemplo: `http://203.0.113.10:8501`

**Atenção ao firewall:** se não abrir, pode ser que a porta 8501 esteja
bloqueada. Libere-a (exemplo usando `ufw`, comum em Ubuntu):

```bash
sudo ufw allow 8501/tcp
```

### 5.2. Via domínio (opcional, recomendado para uso contínuo)

Se você tiver um domínio (ex: `clientes.suaempresa.com.br`) apontando
para o IP do servidor, o ideal é colocar um proxy reverso (Nginx) na
frente do container para servir via HTTPS. Resumo rápido:

1. Aponte o domínio (registro A) para o IP do servidor.
2. Instale o Nginx no servidor: `sudo apt install nginx -y`
3. Configure um `server block` redirecionando para `localhost:8501`.
4. Use o Certbot para gerar certificado HTTPS gratuito:
   ```bash
   sudo apt install certbot python3-certbot-nginx -y
   sudo certbot --nginx -d clientes.suaempresa.com.br
   ```

Esse passo é opcional — o app já funciona perfeitamente via IP e porta
8501 sem isso, mas o proxy com HTTPS é recomendado se for expor para a
internet (fora da rede interna).

---

## PARTE 6 — Atualizando o app no futuro

Sempre que você alterar o código e quiser subir uma nova versão:

**No seu PC (local):**
```bash
git add .
git commit -m "Descrição da alteração"
git push
```

**No servidor:**
```bash
cd gestor-clientes
git pull

docker stop gestor-clientes
docker rm gestor-clientes

docker build -t gestor-clientes:latest .

docker run -d \
  --name gestor-clientes \
  --restart unless-stopped \
  -p 8501:8501 \
  gestor-clientes:latest
```

Pronto — sua nova versão estará no ar.

---

## Resolução de problemas comuns

| Sintoma | Causa provável | Solução |
|---|---|---|
| `docker: command not found` | Docker não instalado corretamente | Repita a Parte 2.2 |
| Página não carrega no navegador | Porta bloqueada no firewall | Libere a porta 8501 (Parte 5.1) |
| `Permission denied` ao rodar `docker` | Usuário não está no grupo docker | Repita `usermod -aG docker` e reconecte o SSH |
| Erro ao clonar `Repository not found` | Repositório privado sem autenticação | Revise Parte 3 (chave SSH ou PAT) |
| Upload de arquivo maior que 50MB falha | Limite configurado no `config.toml` | Ajuste `maxUploadSize` em `.streamlit/config.toml` e refaça o build |
