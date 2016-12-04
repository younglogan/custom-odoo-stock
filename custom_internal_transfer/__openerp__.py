# -*- coding: utf-8 -*-

{
    'name': 'Stock Internal Transfer',
    'version': '1.0',
    'author': 'Tanzil Khan',
    'website': 'https://business-accelerate.com',
    'category': 'Warehouse',
    'sequence': 1,
    'summary': 'This module allows employee to raise requisition for products from store.',
    'depends': ['stock'],
    'installable': True,
    'application': True,
    'auto_install': False,
    'data': [
        'views/custom_internal_transfer_view.xml',
    ],
}
