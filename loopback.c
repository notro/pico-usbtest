// SPDX-License-Identifier: CC0-1.0

#include "usbtest.h"
#include "device/usbd_pvt.h"

static uint8_t _bulk_in;
static uint8_t _bulk_out;
static uint8_t *_bulk_buf;
static size_t _bulk_buf_len;

void usbtest_loopback_init(uint8_t *bulk_buf, size_t bulk_buf_len)
{
    _bulk_buf = bulk_buf;
    _bulk_buf_len = bulk_buf_len;
}

bool usbtest_loopback_enable(uint8_t rhport, tusb_desc_interface_t const * itf_desc)
{
    USBTEST_LOG2("%s:\n", __func__);

    uint8_t const * p_desc = tu_desc_next(itf_desc);
    TU_ASSERT( usbd_open_edpt_pair(rhport, p_desc, 2, TUSB_XFER_BULK, &_bulk_out, &_bulk_in) );
    TU_ASSERT ( usbd_edpt_xfer(rhport, _bulk_out, _bulk_buf, _bulk_buf_len) );
    return true;
}

void usbtest_loopback_disable(uint8_t rhport)
{
    USBTEST_LOG2("%s:\n", __func__);

    if (_bulk_in)
        usbd_edpt_close(rhport, _bulk_in);
    _bulk_in = 0;
    if (_bulk_out)
        usbd_edpt_close(rhport, _bulk_out);
    _bulk_out = 0;
}

bool usbtest_loopback_complete(uint8_t rhport, uint8_t ep_addr, uint32_t xferred_bytes)
{
    USBTEST_LOG2("%s:\n", __func__);

    if (ep_addr == _bulk_out) {
        // Loop back data
        TU_ASSERT ( usbd_edpt_xfer(rhport, _bulk_in, _bulk_buf, xferred_bytes) );
    } else if (ep_addr == _bulk_in) {
        TU_ASSERT ( usbd_edpt_xfer(rhport, _bulk_out, _bulk_buf, _bulk_buf_len) );
    } else {
        return false;
    }
    return true;
}
