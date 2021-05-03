// SPDX-License-Identifier: CC0-1.0

#include "usbtest.h"
#include "device/usbd_pvt.h"

static uint8_t _bulk_in;
static uint8_t _bulk_out;
static uint8_t *_bulk_in_buf;
static uint8_t *_bulk_out_buf;
static size_t _bulk_buf_len;

// FIXME: Add pattern check
// /sys/module/usbtest/parameters/pattern
// MODULE_PARM_DESC(pattern, "0 = all zeroes, 1 = mod63, 2 = none");

static bool usbtest_sourcesink_queue_bulk(uint8_t rhport, bool in)
{
    if (in)
        return usbd_edpt_xfer(rhport, _bulk_in, _bulk_in_buf, _bulk_buf_len);
    else
        return usbd_edpt_xfer(rhport, _bulk_out, _bulk_out_buf, _bulk_buf_len);
}

void usbtest_sourcesink_init(uint8_t *bulk_in_buf, uint8_t *bulk_out_buf, size_t bulk_buf_len)
{
    _bulk_in_buf = bulk_in_buf;
    _bulk_out_buf = bulk_out_buf;
    _bulk_buf_len = bulk_buf_len;
}

bool usbtest_sourcesink_enable(uint8_t rhport, tusb_desc_interface_t const * itf_desc)
{
    USBTEST_LOG2("%s:\n", __func__);

    uint8_t const * p_desc = tu_desc_next(itf_desc);
    TU_ASSERT( usbd_open_edpt_pair(rhport, p_desc, 2, TUSB_XFER_BULK, &_bulk_out, &_bulk_in) );
    TU_ASSERT ( usbtest_sourcesink_queue_bulk(rhport, false) );
    TU_ASSERT ( usbtest_sourcesink_queue_bulk(rhport, true) );

    return true;
}

static void usbtest_sourcesink_disable_endpoint(uint8_t rhport, uint8_t *ep_addr)
{
    if (*ep_addr) {
        usbd_edpt_close(rhport, *ep_addr);
        *ep_addr = 0;
    }
}

void usbtest_sourcesink_disable(uint8_t rhport)
{
    USBTEST_LOG2("%s:\n", __func__);

    usbtest_sourcesink_disable_endpoint(rhport, &_bulk_in);
    usbtest_sourcesink_disable_endpoint(rhport, &_bulk_out);
}

bool usbtest_sourcesink_complete(uint8_t rhport, uint8_t ep_addr, uint32_t xferred_bytes)
{
    USBTEST_LOG2("%s:\n", __func__);

    if (ep_addr == _bulk_out)
        TU_ASSERT ( usbtest_sourcesink_queue_bulk(rhport, false) );
    else if (ep_addr == _bulk_in)
        TU_ASSERT ( usbtest_sourcesink_queue_bulk(rhport, true) );
    else
        return false;

    return true;
}
