# -*- coding: utf-8 -*-
{
    'name': "Extencion Terminal Punto de Venta Sucursales",

    'summary': """Extencion Terminal Punto de Venta Sucursales""",

    'description': """
       Extencion Terminal Punto de Venta con Sucursales
       Colaborador: Ing. Darrell Sojo
    """,
    'version': '1.0',
    'author': 'INM&LDR Soluciones Tecnologicas',
    'category': 'Extension Módulo Terminal Punto de Venta con Sucursales',

    # any module necessary for this one to work correctly
    'depends': ['base','point_of_sale','account'],

    # always loaded
    'data': [
        'vista/pos_config_inherit.xml',
    ],
    'application': True,
}
