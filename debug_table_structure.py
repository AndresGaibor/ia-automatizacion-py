#!/usr/bin/env python3
"""
Debug script to examine the subscriber table DOM structure
"""
from playwright.sync_api import sync_playwright
from src.utils import load_config, crear_contexto_navegador, configurar_navegador
from src.autentificacion import login

def debug_table_structure():
    config = load_config()
    with sync_playwright() as p:
        browser = configurar_navegador(p, False)
        context = crear_contexto_navegador(browser, False)
        page = context.new_page()
        login(page, context=context)
        page.goto('https://acumbamail.com/app/list/1115559/subscriber/list/')

        print('📊 Debugging subscriber table structure...')

        # Find email locators
        email_locators = page.locator('a[href*="/list/subscriber/detail/"]').all()
        print(f'Total emails found: {len(email_locators)}')

        if len(email_locators) > 0:
            first_email = email_locators[0]
            email_text = first_email.text_content()
            print(f'First email: {email_text}')

            # Check different ancestor levels to understand the structure
            for level in range(1, 5):
                try:
                    ancestor = first_email.locator(f'xpath=ancestor::li[{level}]')
                    count = ancestor.count()
                    print(f'\nAncestor li[{level}]: {count} matches')

                    if count > 0:
                        # Get direct children
                        children = ancestor.locator('> *').all()
                        print(f'  Direct children: {len(children)}')

                        for i, child in enumerate(children[:5]):  # First 5 children
                            tag = child.evaluate('el => el.tagName')
                            text_content = child.text_content()
                            text_preview = text_content[:50] if text_content else 'No text'
                            print(f'    Child {i}: <{tag}> "{text_preview}"')

                            # If it's a div, check its children too
                            if tag.lower() == 'div':
                                div_children = child.locator('> *').all()
                                print(f'      Div has {len(div_children)} children')

                except Exception as e:
                    print(f'Error checking ancestor li[{level}]: {e}')

        # Let's also check the overall table structure
        print('\n📋 Overall table structure:')
        ul_elements = page.locator('ul').all()
        print(f'Total UL elements: {len(ul_elements)}')

        for i, ul in enumerate(ul_elements[:3]):  # Check first 3 ULs
            li_children = ul.locator('> li').all()
            print(f'UL {i}: {len(li_children)} direct LI children')

            if len(li_children) > 0:
                first_li = li_children[0]
                li_text = first_li.text_content()
                print(f'  First LI text preview: {li_text[:100] if li_text else "No text"}')

        browser.close()

if __name__ == "__main__":
    debug_table_structure()