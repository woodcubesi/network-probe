# Network Probe para Linux

Pacote para Ubuntu 25 ou distribuicoes proximas baseadas em systemd.

## Instalar como servico local

```bash
sudo bash ./install.sh
```

A aplicacao fica em:

```text
http://127.0.0.1:8081
```

Comandos uteis:

```bash
sudo systemctl status networkprobe
sudo systemctl restart networkprobe
sudo journalctl -u networkprobe -f
```

## Instalar com Nginx

```bash
sudo bash ./install.sh --with-nginx --server-name _
```

O Nginx publica a aplicacao em:

```text
http://IP_DO_SERVIDOR/
```

Para abrir o firewall UFW, se ele estiver ativo:

```bash
sudo bash ./install.sh --with-nginx --open-firewall
```

## Instalar sem Nginx, acessivel pela rede

```bash
sudo bash ./install.sh --listen-host 0.0.0.0 --open-firewall
```

Depois acesse:

```text
http://IP_DO_SERVIDOR:8081
```

## Desinstalar

```bash
sudo bash ./uninstall.sh
```

## Observacoes

- O servico roda com usuario dedicado `networkprobe`.
- O backend usa apenas Python 3 e biblioteca padrao.
- O modo ICMP usa o comando `ping` do sistema.
- O modo Port Scan faz TCP connect scan. Use apenas em hosts onde voce tem autorizacao.
