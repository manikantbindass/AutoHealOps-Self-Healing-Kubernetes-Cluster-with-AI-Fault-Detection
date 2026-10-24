import js from '@eslint/js';
import globals from 'globals';
import react from 'eslint-plugin-react';
import hooks from 'eslint-plugin-react-hooks';
export default [
 {ignores:['build/**','node_modules/**']},
 js.configs.recommended,
 {files:['src/**/*.{js,jsx}'],languageOptions:{ecmaVersion:'latest',sourceType:'module',parserOptions:{ecmaFeatures:{jsx:true}},globals:{...globals.browser,...globals.node,...globals.vitest}},plugins:{react,'react-hooks':hooks},settings:{react:{version:'detect'}},rules:{...react.configs.recommended.rules,...hooks.configs.recommended.rules,'react/prop-types':'off','react/react-in-jsx-scope':'off','no-unused-vars':['error',{argsIgnorePattern:'^_'}]}}
];
