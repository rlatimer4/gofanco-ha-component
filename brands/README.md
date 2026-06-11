# Brand assets for home-assistant/brands

Home Assistant only displays integration logos served from the
[home-assistant/brands](https://github.com/home-assistant/brands) repository —
image files inside the custom component itself are ignored.

To get the logo showing in the HA UI, copy this directory into a fork of
that repository at:

    custom_integrations/gofanco_hdmi_matrix/
        icon.png      (256x256)
        icon@2x.png   (512x512)
        logo.png      (wordmark, 374x96)

and open a pull request. Once merged, HA will pick the images up
automatically (they are served from brands.home-assistant.io).

Generated from `gofanco_logo.jpg` in the repo root (trimmed, background
made transparent, resized).
