import netifaces as ni

def get_ip_address(interface='eth0'):
    return ni.ifaddresses(interface)[ni.AF_INET][0]['addr']
