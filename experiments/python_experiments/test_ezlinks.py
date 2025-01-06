from seleniumbase import SB

# with SB(uc=True, test=True, locale_code="en") as sb:
#     url = "https://cityofaurora.ezlinksgolf.com/index.html#/search"
#     sb.activate_cdp_mode(url)
#     sb.uc_gui_click_captcha()
#     sb.sleep(2)
#     print(sb.cdp.get_text('body'))


# with SB(uc=True, test=True, xvfb=True) as sb:
#     url = "https://cityofaurora.ezlinksgolf.com/index.html#/search"
#     sb.uc_open_with_reconnect(url, 4)
#     sb.uc_gui_click_captcha()
#     print(sb.get_page_title())



with SB(uc=True, test=True, locale_code="en", proxy='juuwqkin:tif49vweo33s@107.172.163.27:6543') as sb:
    url = "https://cityofaurora.ezlinksgolf.com/index.html#/search"
    sb.activate_uc_mode(url)
    sb.sleep(5)
    sb.uc_gui_click_captcha()
    sb.sleep(2)
    print(sb.cdp.get_text('body'))
    sb.sleep(20)