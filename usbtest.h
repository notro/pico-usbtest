// SPDX-License-Identifier: CC0-1.0

#ifndef _USBTEST_H_
#define _USBTEST_H_

#include "common/tusb_common.h"
#include "device/usbd.h"

#define USBTEST_LOG1    printf
#define USBTEST_LOG2    printf

enum usbtest_configuration_index {
    USBTEST_SOURCESINK = 0,
    USBTEST_LOOPBACK = 1,
};

extern uint8_t usbtest_current_configuration_idx;

void usbtest_sourcesink_init(uint8_t *bulk_in_buf, uint8_t *bulk_out_buf, size_t bulk_buf_len);
bool usbtest_sourcesink_enable(uint8_t rhport, tusb_desc_interface_t const * itf_desc);
void usbtest_sourcesink_disable(uint8_t rhport);
bool usbtest_sourcesink_complete(uint8_t rhport, uint8_t ep_addr, uint32_t xferred_bytes);

void usbtest_loopback_init(uint8_t *bulk_buf, size_t bulk_buf_len);
bool usbtest_loopback_enable(uint8_t rhport, tusb_desc_interface_t const * itf_desc);
void usbtest_loopback_disable(uint8_t rhport);
bool usbtest_loopback_complete(uint8_t rhport, uint8_t ep_addr, uint32_t xferred_bytes);

void board_led_activity(void);

#endif
