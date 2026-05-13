# Network Probe

Aplicacao web em Python para testar conectividade TCP, UDP e ICMP, com uso parecido com `tcping64`, interface web e modo continuo.

## Recursos

- Teste TCP por porta, com latencia, perda e jitter.
- Teste UDP com resposta, ICMP/ping e estatisticas por tentativa.
- Modo continuo, equivalente ao `tcping64 -t host porta`.
- Scan TCP de portas abertas em IP, DNS ou FQDN.
- Interface web responsiva em tempo real.
- Backend em Python usando apenas biblioteca padrao.
- Pacote Windows com servico nativo.
- Pacote Linux para Ubuntu 25 com `systemd` e Nginx opcional.

## Estrutura

```text
app.py                         Aplicacao web principal
service.py                     Host de servico Windows
run.ps1                        Execucao local no Windows
installer/                     Scripts de instalacao Windows
linux/                         Scripts e guia Linux
release/NetworkProbe-Service   Pacote Windows pronto
release/NetworkProbe-Linux     Pacote Linux pronto
```

## Instalar no Windows

Use o pacote pronto em `release/NetworkProbe-Service.zip`.

1. Extraia o arquivo ZIP.
2. Abra o PowerShell como Administrador dentro da pasta extraida.
3. Execute:

```powershell
.\install-service.ps1
```

Depois acesse:

```text
http://127.0.0.1:8081
```

Para permitir acesso pela rede:

```powershell
.\install-service.ps1 -ListenHost 0.0.0.0 -PublicFirewall
```

Comandos uteis:

```powershell
Get-Service NetworkProbe
Restart-Service NetworkProbe
Stop-Service NetworkProbe
```

Para remover:

```powershell
.\uninstall-service.ps1
```

Quando `NetworkProbeService.exe` estiver no pacote, a maquina destino nao precisa ter Python instalado.

## Instalar no Linux

Base recomendada: Ubuntu 25 ou distribuicoes proximas com `systemd`.

Use o pacote pronto em `release/NetworkProbe-Linux.tar.gz`.

```bash
tar -xzf NetworkProbe-Linux.tar.gz
cd NetworkProbe-Linux
sudo bash ./install.sh
```

Depois acesse:

```text
http://127.0.0.1:8081
```

Para publicar via Nginx na porta 80:

```bash
sudo bash ./install.sh --with-nginx --open-firewall
```

Para deixar a aplicacao diretamente acessivel pela rede, sem Nginx:

```bash
sudo bash ./install.sh --listen-host 0.0.0.0 --open-firewall
```

Comandos uteis:

```bash
sudo systemctl status networkprobe
sudo systemctl restart networkprobe
sudo journalctl -u networkprobe -f
```

Para remover:

```bash
sudo bash ./uninstall.sh
```

## Rodar em modo desenvolvimento

No Windows:

```powershell
.\run.ps1
```

Ou, se o Python estiver no PATH:

```powershell
python app.py --host 127.0.0.1 --port 8081
```

No Linux:

```bash
python3 app.py --host 127.0.0.1 --port 8081
```

## Uso da interface

Abra a aplicacao no navegador e escolha o modo:

- `Probe`: TCP, UDP ou ICMP.
- `Port Scan`: scan TCP de portas abertas.

No modo `Probe`, marque `Teste continuo (-t)` para manter os testes rodando ate parar manualmente.

No modo `Port Scan`, informe portas como:

```text
22,80,443
1-1024
80,443,8000-8100
```

Use o scan apenas em hosts onde voce tem autorizacao.

## API

Teste TCP/UDP/ICMP:

```text
http://127.0.0.1:8081/api/probe?protocol=tcp&host=google.com&port=443&count=4&timeout=2&interval=1
```

Protocolos aceitos:

```text
tcp, udp, icmp
```

Scan TCP:

```text
http://127.0.0.1:8081/api/scan?host=127.0.0.1&ports=22,80,443,8000-8100&timeout=1&concurrency=100
```

Health check:

```text
http://127.0.0.1:8081/health
```

## Build Windows

O executavel de servico foi gerado com PyInstaller usando `NetworkProbeService.spec`.

Exemplo:

```powershell
pyinstaller NetworkProbeService.spec
```

Depois copie `dist\NetworkProbeService.exe` para o pacote `release\NetworkProbe-Service` junto com os scripts de instalacao.

## Notas

- TCP mede o tempo de abertura da conexao.
- UDP pode ficar inconclusivo se o host nao responder ao payload.
- ICMP usa o comando `ping` do sistema operacional.
- Jitter e a media da diferenca absoluta entre latencias bem-sucedidas consecutivas.
