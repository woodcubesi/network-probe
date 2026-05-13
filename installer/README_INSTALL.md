# Network Probe Installer

Este pacote instala o Network Probe como servico real do Windows usando `NetworkProbeService.exe`.

## Download

Baixe o pacote pronto:

```text
https://github.com/woodcubesi/network-probe/raw/main/release/NetworkProbe-Service.zip
```

## Requisitos

- Windows 10/11 ou Windows Server com PowerShell 5.1 ou superior.
- PowerShell aberto como Administrador.
- Python nao e necessario quando `NetworkProbeService.exe` esta presente no pacote.

## Instalar como servico local

Abra o PowerShell como Administrador na pasta do pacote e rode:

```powershell
.\install-service.ps1
```

Depois acesse:

```text
http://127.0.0.1:8081
```

## Instalar servico para acesso pela rede

```powershell
.\install-service.ps1 -ListenHost 0.0.0.0 -PublicFirewall
```

Depois acesse de outro computador usando:

```text
http://IP_DA_MAQUINA:8081
```

## Desinstalar

Abra o PowerShell como Administrador e rode:

```powershell
.\uninstall-service.ps1
```

## Observacao

O modo `install-service.ps1` cria um servico nativo chamado `NetworkProbe`.
Python nao precisa estar instalado na maquina destino quando `NetworkProbeService.exe` esta presente no pacote.

Comandos uteis:

```powershell
Get-Service NetworkProbe
Restart-Service NetworkProbe
Stop-Service NetworkProbe
```
