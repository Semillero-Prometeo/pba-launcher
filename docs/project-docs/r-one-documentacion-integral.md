# R-ONE: documentación integral

Semillero de investigación Prometeo · Facultad de Ingeniería · Universidad Libre, seccional Bogotá

<!-- pendiente: tarea 8 -->

## Cómo leer este documento

<!-- pendiente: tarea 8 -->

## Versión documentada

| Repositorio | Rama | Commit | Fecha |
|---|---|---|---|
| `pba-launcher` | main | `28900f3` | 2026-11-05 |
| `pmas-web-main` | dev | `8e3c3fb` | 2026-10-27 |
| `pba-ms-gateway` | dev | `3f38ec9` | 2026-10-19 |
| `pba-ms-auth` | dev | `4c4802a` | 2026-10-14 |
| `pba-ms-management` | dev | `d70503c` | 2026-10-27 |
| `pba-ms-robotics` | dev | `05a6e16` | 2026-10-27 |
| `pmai-mai-core` | dev | `e0452ed` | 2026-10-27 |
| `pmai-model-context` | dev | `400ec0d` | 2026-10-09 |
| `pmai-model-vision-language` | dev | `b9042c9` | 2026-10-31 |
| `pmai-model-vision` | dev | `5bbccd6` | 2026-08-27 |
| `pmas-web-motion-studio` | dev | `259451a` | 2026-10-17 |
| `pba-arduino-codes` | dev | `2e9454f` | 2026-04-14 |

## Tabla de contenido

<!-- toc:inicio -->
- [Cómo leer este documento](#cómo-leer-este-documento)
- [Versión documentada](#versión-documentada)
- [Parte I. Entender R-ONE](#parte-i-entender-r-one)
  - [1. Qué es R-ONE y por qué existe](#1-qué-es-r-one-y-por-qué-existe)
  - [2. El sistema en una página](#2-el-sistema-en-una-página)
  - [3. Recorrido de una pregunta](#3-recorrido-de-una-pregunta)
  - [4. Conceptos clave](#4-conceptos-clave)
- [Parte II. Arquitectura y flujos](#parte-ii-arquitectura-y-flujos)
  - [5. Mapa de servicios](#5-mapa-de-servicios)
  - [6. Flujos](#6-flujos)
  - [7. Datos y persistencia](#7-datos-y-persistencia)
- [Parte III. Repositorios](#parte-iii-repositorios)
  - [8. Cómo leer una ficha](#8-cómo-leer-una-ficha)
  - [9. pba-launcher](#9-pba-launcher)
  - [10. pmas-web-main](#10-pmas-web-main)
  - [11. pba-ms-gateway](#11-pba-ms-gateway)
  - [12. pba-ms-auth](#12-pba-ms-auth)
  - [13. pba-ms-management](#13-pba-ms-management)
  - [14. pba-ms-robotics](#14-pba-ms-robotics)
  - [15. pmai-mai-core](#15-pmai-mai-core)
  - [16. pmai-model-context](#16-pmai-model-context)
  - [17. pmai-model-vision-language](#17-pmai-model-vision-language)
  - [18. pmai-model-vision](#18-pmai-model-vision)
  - [19. pmas-web-motion-studio](#19-pmas-web-motion-studio)
  - [20. pba-arduino-codes](#20-pba-arduino-codes)
- [Parte IV. Despliegue y operación](#parte-iv-despliegue-y-operación)
  - [21. Requisitos y configuración](#21-requisitos-y-configuración)
  - [22. Arranque local y en red local](#22-arranque-local-y-en-red-local)
  - [23. La Jetson Orin Nano](#23-la-jetson-orin-nano)
  - [24. Solución de problemas](#24-solución-de-problemas)
- [Parte V. Producto e identidad visual](#parte-v-producto-e-identidad-visual)
  - [25. Para quién es la interfaz](#25-para-quién-es-la-interfaz)
  - [26. Principios y voz](#26-principios-y-voz)
  - [27. Paleta, tipografía y accesibilidad](#27-paleta-tipografía-y-accesibilidad)
- [Parte VI. Evolución e investigación](#parte-vi-evolución-e-investigación)
  - [28. Stakeholders e hitos](#28-stakeholders-e-hitos)
  - [29. El detector de objetos](#29-el-detector-de-objetos)
  - [30. El modelo contextual](#30-el-modelo-contextual)
  - [31. El modelo de acción](#31-el-modelo-de-acción)
  - [32. La primera interfaz y las decisiones descartadas](#32-la-primera-interfaz-y-las-decisiones-descartadas)
- [Anexos](#anexos)
  - [Anexo A. Glosario](#anexo-a-glosario)
  - [Anexo B. Variables de entorno](#anexo-b-variables-de-entorno)
  - [Anexo C. Patrones NATS](#anexo-c-patrones-nats)
  - [Anexo D. Endpoints HTTP del gateway](#anexo-d-endpoints-http-del-gateway)
  - [Anexo E. Índice de figuras y diagramas](#anexo-e-índice-de-figuras-y-diagramas)
<!-- toc:fin -->

## Parte I. Entender R-ONE

<!-- pendiente: tarea 8 -->

### 1. Qué es R-ONE y por qué existe

#### 1.1 El semillero Prometeo

<!-- pendiente: tarea 8 -->

#### 1.2 Objetivos del proyecto

<!-- pendiente: tarea 8 -->

#### 1.3 Qué puede hacer R-ONE hoy

<!-- pendiente: tarea 8 -->

### 2. El sistema en una página

<!-- pendiente: tarea 8 -->

### 3. Recorrido de una pregunta

<!-- pendiente: tarea 8 -->

### 4. Conceptos clave

#### 4.1 Microservicios y gateway

<!-- pendiente: tarea 8 -->

#### 4.2 NATS y los patrones de mensaje

<!-- pendiente: tarea 8 -->

#### 4.3 Sesión y JWT

<!-- pendiente: tarea 8 -->

#### 4.4 Detección, seguimiento y reidentificación

<!-- pendiente: tarea 8 -->

#### 4.5 Descripción de escena

<!-- pendiente: tarea 8 -->

#### 4.6 Embeddings y búsqueda vectorial

<!-- pendiente: tarea 8 -->

#### 4.7 Caché semántico

<!-- pendiente: tarea 8 -->

#### 4.8 Modelo local frente a modelo en la nube

<!-- pendiente: tarea 8 -->

#### 4.9 Secuencias, bloques y el par normal y neutro

<!-- pendiente: tarea 8 -->

## Parte II. Arquitectura y flujos

<!-- pendiente: tarea 9 -->

### 5. Mapa de servicios

#### 5.1 Servicios y puertos

<!-- pendiente: tarea 9 -->

#### 5.2 Canales de comunicación

<!-- pendiente: tarea 9 -->

### 6. Flujos

#### 6.1 Inicio de sesión

<!-- pendiente: tarea 9 -->

#### 6.2 Chat por la ruta Básico

<!-- pendiente: tarea 9 -->

#### 6.3 Chat por la ruta Complejo: el turno

<!-- pendiente: tarea 9 -->

#### 6.4 El micrófono

<!-- pendiente: tarea 9 -->

#### 6.5 Ciclo de un gesto

<!-- pendiente: tarea 9 -->

#### 6.6 Visión en tiempo real

<!-- pendiente: tarea 9 -->

#### 6.7 Creación e ingesta de una secuencia

<!-- pendiente: tarea 9 -->

#### 6.8 Declarar un poema

<!-- pendiente: tarea 9 -->

### 7. Datos y persistencia

#### 7.1 Postgres y Prisma

<!-- pendiente: tarea 9 -->

#### 7.2 Milvus Lite

<!-- pendiente: tarea 9 -->

#### 7.3 Secuencias en JSON

<!-- pendiente: tarea 9 -->

#### 7.4 Ruta del chat

<!-- pendiente: tarea 9 -->

#### 7.5 Modelos de IA en disco

<!-- pendiente: tarea 9 -->

## Parte III. Repositorios

<!-- pendiente: tarea 10 -->

### 8. Cómo leer una ficha

<!-- pendiente: tarea 10 -->

### 9. pba-launcher

<!-- pendiente: tarea 10 -->

### 10. pmas-web-main

<!-- pendiente: tarea 10 -->

### 11. pba-ms-gateway

<!-- pendiente: tarea 10 -->

### 12. pba-ms-auth

<!-- pendiente: tarea 10 -->

### 13. pba-ms-management

<!-- pendiente: tarea 10 -->

### 14. pba-ms-robotics

<!-- pendiente: tarea 10 -->

### 15. pmai-mai-core

<!-- pendiente: tarea 11 -->

### 16. pmai-model-context

<!-- pendiente: tarea 11 -->

### 17. pmai-model-vision-language

<!-- pendiente: tarea 11 -->

### 18. pmai-model-vision

<!-- pendiente: tarea 11 -->

### 19. pmas-web-motion-studio

<!-- pendiente: tarea 11 -->

### 20. pba-arduino-codes

<!-- pendiente: tarea 11 -->

## Parte IV. Despliegue y operación

<!-- pendiente: tarea 12 -->

### 21. Requisitos y configuración

<!-- pendiente: tarea 12 -->

### 22. Arranque local y en red local

<!-- pendiente: tarea 12 -->

### 23. La Jetson Orin Nano

<!-- pendiente: tarea 12 -->

### 24. Solución de problemas

<!-- pendiente: tarea 12 -->

## Parte V. Producto e identidad visual

<!-- pendiente: tarea 13 -->

### 25. Para quién es la interfaz

<!-- pendiente: tarea 13 -->

### 26. Principios y voz

<!-- pendiente: tarea 13 -->

### 27. Paleta, tipografía y accesibilidad

<!-- pendiente: tarea 13 -->

## Parte VI. Evolución e investigación

<!-- pendiente: tarea 13 -->

### 28. Stakeholders e hitos

<!-- pendiente: tarea 13 -->

### 29. El detector de objetos

#### 29.1 Captura y extracción de imágenes

<!-- pendiente: tarea 13 -->

#### 29.2 Etiquetado en Label Studio

<!-- pendiente: tarea 13 -->

#### 29.3 Análisis del dataset

<!-- pendiente: tarea 13 -->

#### 29.4 Limpieza y preprocesamiento

<!-- pendiente: tarea 13 -->

#### 29.5 Entrenamiento y aumento de datos

<!-- pendiente: tarea 13 -->

#### 29.6 Resultados

<!-- pendiente: tarea 13 -->

#### 29.7 Despliegue en mai-core

<!-- pendiente: tarea 13 -->

### 30. El modelo contextual

#### 30.1 Elección del modelo

<!-- pendiente: tarea 13 -->

#### 30.2 Pruebas de BLIP-base y Geospace

<!-- pendiente: tarea 13 -->

#### 30.3 Optimización e inferencia

<!-- pendiente: tarea 13 -->

#### 30.4 Alucinaciones y palabras protegidas

<!-- pendiente: tarea 13 -->

### 31. El modelo de acción

#### 31.1 Fase de análisis

<!-- pendiente: tarea 13 -->

#### 31.2 Ingesta por web scraping

<!-- pendiente: tarea 13 -->

#### 31.3 Búsqueda semántica y caché

<!-- pendiente: tarea 13 -->

#### 31.4 Ingeniería del prompt

<!-- pendiente: tarea 13 -->

#### 31.5 Métricas

<!-- pendiente: tarea 13 -->

### 32. La primera interfaz y las decisiones descartadas

<!-- pendiente: tarea 13 -->

## Anexos

### Anexo A. Glosario

<!-- pendiente: tarea 14 -->

### Anexo B. Variables de entorno

<!-- pendiente: tarea 14 -->

### Anexo C. Patrones NATS

<!-- pendiente: tarea 14 -->

### Anexo D. Endpoints HTTP del gateway

<!-- pendiente: tarea 14 -->

### Anexo E. Índice de figuras y diagramas

<!-- pendiente: tarea 14 -->
