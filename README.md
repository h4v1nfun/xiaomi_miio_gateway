# xiaomi_miio_gateway
Home Assistant Xiaomi Gateway Radio

This is a custom component to play/stop the Network radio in a Xiaomi Gateway

this plays the last played station on the gateway

follow this to get custom radios in the gateway ->
http://ximiraga.ru


# Installation:
Follow only one of these installation methods.

<details>
  <summary><b>Installation and tracking with HACS:</b></summary>

1. You can install this custom component by adding this repository (https://github.com/h4v1nfun/xiaomi_miio_gateway) to HACS in the settings menu of HACS first. You will find the custom component in the integration menu afterwards, look for 'Xiaomi Mi Gateway Radio Media Player'.

2. Set the configuration.yaml
</details>

<details>
  <summary><b>Manual installation:</b></summary>
  
1. Copy xiaomi_gateway_radio into custom_components

2. Set the configuration.yaml
</details>

configuration.yaml example
```yaml
media_player:
  - platform: xiaomi_gateway_radio
    host: <ip of gateway>
    token: <gateway token>
```

token is obtained the same way as explained here ->
https://www.home-assistant.io/components/vacuum.xiaomi_miio/#retrieving-the-access-token

Contributors:

https://github.com/VedgeKonn

https://github.com/glebsterx

https://github.com/fufar
