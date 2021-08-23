// SPDX-License-Identifier: CC0-1.0

#include <string.h>
#include "tusb.h"

enum string_index {
    RESERVED_IDX = 0,
    MANUFACTURER_IDX,
    PRODUCT_IDX,
    SERIALNUMBER_IDX,
    SOURCE_SINK_IDX,
};

tusb_desc_device_t const device_descriptor = {
    .bLength            = sizeof(tusb_desc_device_t),
    .bDescriptorType    = TUSB_DESC_DEVICE,
    .bcdUSB          	= 0x0110,

    .bDeviceClass    	= TUSB_CLASS_VENDOR_SPECIFIC,
    .bDeviceSubClass 	= 0,
    .bDeviceProtocol 	= 0,
    .bMaxPacketSize0 	= 64,

    .idVendor        	= 0x0525, // NetChip
    .idProduct       	= 0xa4a0, // Linux-USB "Gadget Zero"
    .bcdDevice       	= 0,

    .iManufacturer      = MANUFACTURER_IDX,
    .iProduct           = PRODUCT_IDX,
    .iSerialNumber 	    = SERIALNUMBER_IDX,

    .bNumConfigurations = 1,
};

uint8_t const *tud_descriptor_device_cb(void)
{
    return (uint8_t const *) &device_descriptor;
}

#define USBTEST_ENDPOINT_DESCRIPTOR(_attr, _addr, _size, _interval)  \
    {                                                               \
        .bLength = sizeof(tusb_desc_endpoint_t),                    \
        .bDescriptorType = TUSB_DESC_ENDPOINT,                      \
        .bEndpointAddress = _addr,                                  \
        .bmAttributes = _attr,                                      \
        .wMaxPacketSize.size = _size,                               \
        .bInterval = _interval,                                     \
    }

#define USBTEST_BULK_DESCRIPTOR(_addr) \
    USBTEST_ENDPOINT_DESCRIPTOR(TUSB_XFER_BULK, _addr, CFG_USBTEST_BULK_ENPOINT_SIZE, 0)

typedef struct TU_ATTR_PACKED {
    tusb_desc_configuration_t config;
    tusb_desc_interface_t interface;
    tusb_desc_endpoint_t bulk_in;
    tusb_desc_endpoint_t bulk_out;
} usbtest_source_sink_config_descriptor_t;

usbtest_source_sink_config_descriptor_t source_sink_config_descriptor = {
    .config = {
        .bLength = sizeof(tusb_desc_configuration_t),
        .bDescriptorType = TUSB_DESC_CONFIGURATION,
        .wTotalLength = sizeof(usbtest_source_sink_config_descriptor_t),
        .bNumInterfaces = 1,
        .bConfigurationValue = 1,
        .iConfiguration = SOURCE_SINK_IDX,
        .bmAttributes = TU_BIT(7) | TUSB_DESC_CONFIG_ATT_SELF_POWERED,
        .bMaxPower = 100 / 2,
    },

    .interface = {
        .bLength = sizeof(tusb_desc_interface_t),
        .bDescriptorType = TUSB_DESC_INTERFACE,
        .bInterfaceNumber = 0,
        .bAlternateSetting = 0,
        .bNumEndpoints = 2,
        .bInterfaceClass = TUSB_CLASS_VENDOR_SPECIFIC,
        .bInterfaceSubClass = 0x00,
        .bInterfaceProtocol = 0x00,
        .iInterface = 0,
    },

    .bulk_in = USBTEST_BULK_DESCRIPTOR(0x81),
    .bulk_out = USBTEST_BULK_DESCRIPTOR(0x01),
};

uint8_t const * tud_descriptor_configuration_cb(uint8_t index)
{
    //printf("%s: index=%u\n", __func__, index);

    return (uint8_t const *)&source_sink_config_descriptor;
}

typedef struct TU_ATTR_PACKED
{
    uint8_t bLength;
    uint8_t bDescriptorType;
    uint16_t unicode_string[31];
} gud_desc_string_t;

static gud_desc_string_t string_descriptor = {
    .bDescriptorType = TUSB_DESC_STRING,
};

static const char *strings[] = {
    "",
    [MANUFACTURER_IDX] = "Raspberry Pi Pico",
    [PRODUCT_IDX] = "Gadget Zero",
    [SERIALNUMBER_IDX] = "0123456789.0123456789.0123456789",
    [SOURCE_SINK_IDX] = "source and sink data",
};

uint16_t const *tud_descriptor_string_cb(uint8_t index, uint16_t langid)
{
    (void) langid;

    if (index >= TU_ARRAY_SIZE(strings))
        return NULL;

    if (index == 0) {
        string_descriptor.bLength = 4;
        string_descriptor.unicode_string[0] = 0x0409;
        return (uint16_t *)&string_descriptor;
    }

    const char *str = strings[index];

    uint8_t len = strlen(str);
    if (len > sizeof(string_descriptor.unicode_string))
        len = sizeof(string_descriptor.unicode_string);

    string_descriptor.bLength = 2 + 2 * len;

    for (uint8_t i = 0; i < len; i++)
      string_descriptor.unicode_string[i] = str[i];

    return (uint16_t *)&string_descriptor;
}
