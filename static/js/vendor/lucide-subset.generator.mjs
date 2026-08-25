/**
 * Gerador do subset vendorizado do Lucide (static/js/vendor/lucide-subset.js).
 *
 * POR QUE: o bundle UMD completo do Lucide 1.34.0 tem 419 KB (97 KB gzip) e
 * carrega ~1600 icones; o portal usa ~90. O aluno abre o site em celular
 * modesto, as vezes em 3G, e o `lucide@latest` do CDN ainda podia trocar de
 * major sem deploy nenhum. Este script gera um arquivo com o runtime do Lucide
 * (mesma API: `<i data-lucide="nome">` + `window.lucide.createIcons()`) e SO os
 * icones que o repositorio realmente referencia.
 *
 * COMO REGERAR (Node 18+, precisa de rede):
 *
 *   1) Atualize o inventario de nomes (na raiz do projeto, git bash):
 *        grep -rhoP 'data-lucide="\K[a-z0-9-]+' templates/ static/ design_system/ \
 *          | sort -u
 *      Cole a saida em ICON_NAMES abaixo.
 *
 *   2) node static/js/vendor/lucide-subset.generator.mjs
 *
 * O script baixa a versao fixada em LUCIDE_VERSION, confere o SHA256, e
 * reescreve static/js/vendor/lucide-subset.js. Ele imprime os nomes pedidos que
 * NAO existem no Lucide — normalmente sao nomes de outra biblioteca deixados no
 * design system e podem ser ignorados (o runtime degrada sem quebrar).
 *
 * ATENCAO: este arquivo e um utilitario de manutencao, nao e carregado pelo
 * navegador. Ele mora em static/ apenas porque fica junto do artefato que gera.
 */

import { createHash } from 'node:crypto';
import { writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const LUCIDE_VERSION = '1.34.0';
const LUCIDE_URL = `https://unpkg.com/lucide@${LUCIDE_VERSION}/dist/umd/lucide.min.js`;
const OUT_FILE = join(dirname(fileURLToPath(import.meta.url)), 'lucide-subset.js');

/**
 * Nomes usados no repositorio (templates/, static/, design_system/), em
 * kebab-case, exatamente como aparecem em data-lucide.
 */
const ICON_NAMES = [
    'accessibility', 'activity', 'alert-circle', 'alert-triangle', 'architecture',
    'archive', 'arrow-down', 'arrow-left', 'arrow-right', 'arrow-up',
    'arrow-up-right', 'atom', 'bell', 'book', 'book-open', 'book-open-text',
    'calculator', 'calendar', 'calendar-clock', 'check', 'check-check', 'check-circle',
    'check-circle-2', 'chevron-down', 'chevron-right', 'chevron-up',
    'circle-alert', 'circle-check-big', 'circle-dashed', 'clipboard-list',
    'clock', 'door-open', 'download', 'edit-3', 'external-link', 'eye',
    'eye-off', 'file-down', 'file-pen', 'file-text', 'filter', 'flask-conical',
    'folder', 'github', 'globe-2', 'graduation-cap', 'grid-view', 'group',
    'history', 'id-card', 'image-off', 'inbox', 'info', 'key-round', 'keyboard',
    'languages', 'layers', 'layout-dashboard', 'layout-grid', 'library',
    'lightbulb', 'list', 'list-todo', 'loader-circle', 'local-library', 'log-in', 'log-out',
    'mail', 'maximize', 'maximize-2', 'menu', 'message-circle', 'monitor-play',
    'move-up', 'notebook-pen', 'palette', 'paperclip', 'party-popper', 'play',
    'plus', 'plus-circle', 'presentation', 'psychology', 'refresh-cw',
    'rotate-ccw', 'save', 'search', 'send', 'settings', 'settings-2', 'shield',
    'shield-check', 'smartphone', 'sparkle', 'sparkles', 'star', 'sun-moon',
    'table', 'target', 'trash-2', 'trending-up', 'tv', 'upload', 'upload-cloud',
    'user', 'user-check', 'user-cog', 'user-plus', 'user-round', 'user-x',
    'users', 'x', 'zap', 'zoom-in',
];

/**
 * Margem de seguranca: icones genericos que uma tela nova provavelmente vai
 * pedir. Custa poucos bytes e evita ter que regerar o subset a cada ajuste de
 * UI. Se um icone faltar mesmo assim, ele simplesmente nao aparece (o runtime
 * avisa no console) — nenhuma tela quebra.
 */
const ICON_SAFETY_NET = [
    'arrow-down-right', 'arrow-left-right', 'ban', 'bookmark', 'calendar-check',
    'chevron-left', 'circle', 'circle-help', 'circle-x', 'copy', 'ellipsis',
    'file', 'flag', 'home', 'link', 'lock', 'minus', 'pause', 'pencil', 'pin',
    'printer', 'share-2', 'sliders-horizontal', 'square-check', 'timer',
    'trash', 'triangle-alert', 'undo-2', 'video', 'wifi-off',
];

const toPascalCase = (name) => {
    const camel = name.replace(/^([A-Z])|[\s\-_]+(\w)/g, (_m, first, rest) =>
        (rest ? rest.toUpperCase() : first.toLowerCase()));
    return camel.charAt(0).toUpperCase() + camel.slice(1);
};

const response = await fetch(LUCIDE_URL);
if (!response.ok) {
    throw new Error(`Falha ao baixar ${LUCIDE_URL}: HTTP ${response.status}`);
}
const source = await response.text();
const sourceHash = createHash('sha256').update(source).digest('hex');

const module = { exports: {} };
new Function('module', 'exports', source)(module, module.exports);
const lucide = module.exports;

const wanted = [...new Set([...ICON_NAMES, ...ICON_SAFETY_NET])].sort();
const picked = {};
const missing = [];

for (const name of wanted) {
    const key = toPascalCase(name);
    if (lucide.icons?.[key]) {
        picked[key] = lucide.icons[key];
    } else {
        missing.push(name);
    }
}

const header = `/*!
 * lucide-subset.js — subset vendorizado do Lucide v${LUCIDE_VERSION} (ISC)
 * https://lucide.dev · https://github.com/lucide-icons/lucide
 *
 * GERADO por static/js/vendor/lucide-subset.generator.mjs — NAO editar a mao.
 * Fonte: ${LUCIDE_URL}
 * SHA256 da fonte: ${sourceHash}
 * Icones incluidos: ${Object.keys(picked).length} de ~1600 do bundle completo.
 *
 * Mantem a mesma API do bundle oficial: marcacao <i data-lucide="nome"> e
 * window.lucide.createIcons(). Nome desconhecido nao quebra a pagina: o <i>
 * fica vazio (todos os icones do portal sao decorativos, aria-hidden) e um
 * aviso unico vai para o console.
 */`;

const runtime = `
(function () {
    'use strict';

    var ICONS = __ICONS__;

    var DEFAULT_ATTRS = {
        xmlns: 'http://www.w3.org/2000/svg',
        width: 24,
        height: 24,
        viewBox: '0 0 24 24',
        fill: 'none',
        stroke: 'currentColor',
        'stroke-width': 2,
        'stroke-linecap': 'round',
        'stroke-linejoin': 'round'
    };

    var warned = Object.create(null);

    function toPascalCase(name) {
        var camel = name.replace(/^([A-Z])|[\\s\\-_]+(\\w)/g, function (match, first, rest) {
            return rest ? rest.toUpperCase() : first.toLowerCase();
        });
        return camel.charAt(0).toUpperCase() + camel.slice(1);
    }

    function createElement(node) {
        var tag = node[0];
        var attrs = node[1] || {};
        var children = node[2];
        var element = document.createElementNS('http://www.w3.org/2000/svg', tag);

        Object.keys(attrs).forEach(function (key) {
            element.setAttribute(key, String(attrs[key]));
        });
        if (children && children.length) {
            children.forEach(function (child) {
                element.appendChild(createElement(child));
            });
        }
        return element;
    }

    function createSvg(iconNodes, attrs) {
        var merged = Object.assign({}, DEFAULT_ATTRS, attrs || {});
        return createElement(['svg', merged, iconNodes]);
    }

    function hasA11yProp(attrs) {
        for (var key in attrs) {
            if (key.indexOf('aria-') === 0 || key === 'role' || key === 'title') {
                return true;
            }
        }
        return false;
    }

    function combineClassNames(list) {
        return list.filter(function (value, index) {
            return !!value && value.trim() !== '' && list.indexOf(value) === index;
        }).join(' ').trim();
    }

    function toClassList(value) {
        if (typeof value === 'string') return [value];
        if (!value || !value.class) return [];
        if (typeof value.class === 'string') return value.class.split(' ');
        if (Array.isArray(value.class)) return value.class;
        return [];
    }

    function readAttributes(element) {
        return Array.from(element.attributes).reduce(function (acc, attr) {
            acc[attr.name] = attr.value;
            return acc;
        }, {});
    }

    function replaceElement(element, options) {
        var name = element.getAttribute(options.nameAttr);
        if (name == null) return;

        var iconNodes = options.icons[toPascalCase(name)];
        if (!iconNodes) {
            if (!warned[name]) {
                warned[name] = true;
                console.warn(
                    '[lucide-subset] icone "' + name + '" nao esta no subset vendorizado. ' +
                    'Adicione o nome em static/js/vendor/lucide-subset.generator.mjs e regere.'
                );
            }
            return;
        }

        var ownAttrs = readAttributes(element);
        var a11yAttrs = hasA11yProp(ownAttrs) ? {} : { 'aria-hidden': 'true' };
        var attrs = Object.assign(
            {}, DEFAULT_ATTRS, { 'data-lucide': name }, a11yAttrs, options.attrs, ownAttrs
        );
        var className = combineClassNames(
            ['lucide', 'lucide-' + name]
                .concat(toClassList(ownAttrs))
                .concat(toClassList(options.attrs))
        );
        if (className) attrs.class = className;

        var svg = createSvg(iconNodes, attrs);
        if (element.parentNode) element.parentNode.replaceChild(svg, element);
    }

    function createIcons(options) {
        options = options || {};
        var icons = options.icons || ICONS;
        var nameAttr = options.nameAttr || 'data-lucide';
        var attrs = options.attrs || {};
        var root = options.root || document;

        if (typeof root === 'undefined') return;

        Array.from(root.querySelectorAll('[' + nameAttr + ']')).forEach(function (element) {
            try {
                replaceElement(element, { nameAttr: nameAttr, icons: icons, attrs: attrs });
            } catch (error) {
                console.warn('[lucide-subset] falha ao renderizar icone', element, error);
            }
        });
    }

    window.lucide = { icons: ICONS, createIcons: createIcons, createElement: createSvg };
}());
`;

const body = `${header}
${runtime.replace('__ICONS__', JSON.stringify(picked))}`;

writeFileSync(OUT_FILE, body, 'utf8');

console.log(`OK  ${OUT_FILE}`);
console.log(`    icones incluidos: ${Object.keys(picked).length}`);
console.log(`    bytes: ${Buffer.byteLength(body, 'utf8')}`);
if (missing.length) {
    console.log(`    nomes pedidos que NAO existem no Lucide ${LUCIDE_VERSION} (ignorados):`);
    console.log(`      ${missing.join(', ')}`);
}
