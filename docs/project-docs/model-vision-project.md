1. TÍTULO.  

Desarrollo de un modelo de IA y visión artificial para reconocimiento automático de objetos en entornos reales

2. INTRODUCCIÓN.  

Esta investigación parte de realizar el desarrollo de un modelo de inteligencia artificial basado en visión por computador para el reconocimiento automático de objetos y personas en entornos reales. 

Bajo un modelo iterativo de investigación desarrollo fundamentado en tres fases.

Fase 1.  Desarrollo propio de un modelo de inteligencia artificial basado en visión por computador para el reconocimiento automático de objetos en entornos reales fundamentado en redes neuronales convolucionales profundas (CNN) y entrenado con un dataset propio recolectado por integrantes del semillero. 

Fase 2. Mejora del modelo de inteligencia artificial basado en visión por computador desarrollado con la implementación de técnicas de preprocesamiento y estandarización de imágenes, data augmentation con transformaciones fotométricas y geométricas junto a un aumento exponencial del dataset propio utilizado durante las fases de entrenamiento del modelo.

Fase 3. El modelo de visión combina cuatro componentes complementarios. La detección y localización de rostros se realiza mediante BlazeFace (MediaPipe), capaz de identificar múltiples personas en escena con latencia inferior a 15 ms. Sobre el rostro detectado, la biblioteca face_recognition (basada en el modelo ResNet-34 de dlib) genera embeddings de 128 dimensiones que permiten distinguir entre usuarios conocidos y desconocidos mediante comparación de distancia euclidiana, con un umbral de reconocimiento calibrado en 0.5. Paralelamente, DeepFace analiza el estado emocional del interlocutor, clasificándolo en siete categorías (alegría, tristeza, enojo, sorpresa, miedo, disgusto y neutro), mientras que MediaPipe HandLandmarker interpreta gestos de mano a partir de 21 puntos clave articulares, reconociendo señales como palma abierta, puño cerrado o pulgar arriba.


3.  PLANTEAMIENTO DEL PROBLEMA. 

Actualmente la Universidad Libre de Colombia, en la seccional Bogotá D.C sede Bosque Popular, cuenta con un androide de propósito general denominado R-ONE, que tendrá múltiples funciones que van desde la interacción con los visitantes y miembros de la universidad hasta la orientación en procesos internos y administrativos

Actualmente el androide no cuenta con la capacidad de reconocer objetos, lo cual sería vital para identificar atributos físicos de las personas que interactúen con este, por lo cual se ha optado por integrar cámaras conectadas a una red neuronal convolucional (CNN) con el fin de identificar el entorno en el cual se encuentra el androide y de esta forma hacer más amena la interacción con este.

Sin embargo, cada integración de los modelos de visión artificial debe ser probada previamente en un prototipo homologo con el fin de certificar y asegurar el funcionamiento antes de la integración final con R-ONE. 

4. JUSTIFICACIÓN. 

La relevancia académica de este proyecto radica en su contribución al campo de la visión artificial aplicada a la robótica de servicio en entornos educativos, específicamente en la optimización de arquitecturas CNN para el reconocimiento de objetos en plataformas con recursos computacionales limitados, abriendo camino a futuras expansiones funcionales del androide R-ONE, previamente probadas y aseguradas en el prototipo CLAUD-IA.

En ámbitos generales, la aplicación de este modelo en contextos reales puede generar reducciones significativas en costos asociados a procesos de inspección, clasificación, seguridad industrial y logística, al automatizar tareas repetitivas y de alto costo actualmente realizadas por humanos. Sectores como la manufactura, la agricultura de precisión y el control de calidad se beneficiarían de una mayor eficiencia operativa y una reducción de desperdicios. 

Desde una perspectiva social, la automatización del reconocimiento de objetos puede contribuir a mejorar la seguridad en espacios públicos, universidades, hospitales, sistemas de transporte y entornos laborales. Asimismo, libera tiempo humano para labores creativas o de supervisión, aunque plantea desafíos en materia de adaptación laboral y capacitación en nuevas competencias. 


5.  OBJETIVOS. 

Objetivo General
Desarrollar un modelo de IA y visión artificial para el reconocimiento automático de objetos y personas en entornos reales


Objetivos Específicos.

-	Analizar las técnicas actuales de reconocimiento de objetos y limitaciones en entornos reales.
-	Desarrollar un modelo de IA basado en redes neuronales convolucionales para el reconocimiento de objetos y entrenarlo.
-	Implementar el modelo al prototipo físico Claud-IA, a través de la creación de la cabeza
-	Evaluar el modelo desarrollado en diversos escenarios reales para medir su precisión y eficiencia.


6. REFERENTE TEÓRICO. 

En la literatura sobre visión artificial basada en redes neuronales convolucionales (CNN), diversos estudios respaldan un flujo metodológico que parte de un dataset propio, seguido de fases de preprocesamiento y aumento de datos antes del entrenamiento del modelo. Tabassum et al. (2026) desarrollaron y evaluaron una CNN personalizada sobre cinco datasets heterogéneos, aplicando un pipeline de preprocesamiento consistente en preparación del dataset, redimensionamiento, normalización y aumento de datos (rotación, volteo horizontal y ajuste de color) para garantizar comparabilidad y robustez del modelo. 

De forma similar, Avro et al. (2026) diseñaron una CNN personalizada entrenada desde cero para clasificación de imágenes multidominio, destacando cómo las decisiones arquitectónicas y el preprocesamiento adecuado influyen en la capacidad de generalización del modelo. Estos antecedentes sustentan que la construcción de un dataset propio, acompañada de preprocesamiento y aumento de datos, constituye una práctica metodológica consolidada en el desarrollo de modelos de visión artificial basados en CNN.

7.  METODOLOGÍA.

Tipo y diseño de investigación. 

Se desarrolla bajo un enfoque mixto, mediante una investigación-desarrollo (I+D) que combina ciclos de indagación teórica con la construcción y evaluación tecnológica del modelo en campo. 

Este proceso se estructuró bajo la metodología ágil Scrum, la cual permitió organizar el trabajo en sprints iterativos correspondientes a las fases del proyecto: en la Fase 1, un ciclo de investigación derivó en el desarrollo inicial del modelo de reconocimiento de objetos basado en CNN; en la Fase 2, una nueva etapa de indagación permitió la incorporación de técnicas de preprocesamiento y data augmentation para mejorar el modelo previamente construido. 

Paralelamente, en la Fase 3 se adelanta la investigación e implementación de modelos de reconocimiento gestual sobre el prototipo CALUD-IA, desarrollado por el semillero. Este esquema iterativo, propio de Scrum, permitió validar y ajustar el modelo de forma incremental antes de su integración al prototipo CLAUD-IA.

Población y muestra. 
La población de referencia corresponde al universo de imágenes de rostros que pueden recolectarse dentro del entorno de la Universidad Libre, sede Bosque Popular, particularmente de los integrantes del semillero de investigación. La muestra se conformó por un dataset propio de 802 imágenes, distribuidas en 25 clases correspondientes a los rostros de los integrantes, capturados en distintos ambientes y condiciones. La selección de la muestra se realizó por disponibilidad y conveniencia, dado el acceso directo a los integrantes del semillero como sujetos de recolección.

Técnicas de recolección de datos. 
La recolección de imágenes se realizó mediante cámaras de dispositivos celulares, y el proceso de captura y etiquetado fue efectuado manualmente por los integrantes del semillero, empleando anotaciones tipo bounding box en formato YOLO. Esta recolección se limitó estrictamente a la obtención de imágenes destinadas al entrenamiento del modelo, sin la aplicación de instrumentos adicionales como encuestas o pruebas de usabilidad. El dataset resultante fue dividido en tres subconjuntos: 80 % para entrenamiento, 10 % para validación y 10 % para prueba, con el fin de garantizar una evaluación objetiva del desempeño del modelo durante y después del proceso de entrenamiento.


8.  RESULTADOS. 

Durante el entrenamiento del modelo, las métricas registradas muestran un comportamiento óptimo de convergencia y desempeño. Las pérdidas de entrenamiento y validación (box_loss, cls_loss, dfl_loss) presentan una disminución progresiva y estable a lo largo de las 60 épocas, evidenciando un ajuste efectivo de los parámetros sin signos de sobreajuste. 

En cuanto a las métricas de rendimiento, el modelo alcanzó una precisión de 0.8486, un recall de 0.9474, y valores de mAP50 y mAP50-95 de 0.9942 y 0.8677 respectivamente, indicando una alta capacidad de detección y localización de objetos en distintos umbrales de evaluación. 

Estos resultados confirman que el modelo logró una generalización sólida y un rendimiento consistente, respaldado por un proceso de entrenamiento eficiente sobre GPU.

  

  

Métricas y curvas de entrenamiento del modelo YOLO a lo largo de las 60 épocas.

   
 

El desarrollo del sistema de visión y gestos integrados en la cabeza del androide R-One (CLAUD-IA) permitió obtener los siguientes resultados en las dimensiones técnica, funcional y de interacción.
Integración funcional del pipeline de percepción-actuación
Se logró integrar en un único bucle de tiempo real —implementado en el módulo inmoov_vision.py— cuatro procesos de visión artificial que operan de manera simultánea sobre hardware de escritorio convencional: detección de rostros (BlazeFace/MediaPipe), reconocimiento de identidad (face_recognition/dlib), clasificación de emociones (DeepFace) y reconocimiento de gestos de mano (MediaPipe HandLandmarker). La ejecución paralela mediante hilos independientes para las tareas de mayor latencia (clasificación emocional y parpadeo automático) permitió mantener una respuesta perceptiva con una latencia de seguimiento inferior a 200 ms, adecuada para interacción humano-robot en tiempo real.
Calibración y control de los servomotores faciales
Se caracterizaron y calibraron los 14 servomotores faciales del módulo PCA3 (párpados superior e inferior, pupilas, cejas, mejillas y frente), determinando para cada uno sus valores de mínimo, neutro y máximo mediante un protocolo sistemático que garantiza seguridad mecánica y evita bloqueos por sobreextensión. El control de orientación del cuello mediante PID (Kp=0.20, Ki=0.002, Kd=0.08), ajustado por el método de Ziegler-Nichols simplificado, produjo un seguimiento estable y sin oscilaciones perceptibles ante movimientos de personas a velocidad normal de caminata. El umbral de reconocimiento facial se calibró en 0.5, valor que ofreció el mejor balance entre falsos positivos y falsos negativos bajo condiciones de iluminación interior controlada.
Repertorio de gestos reactivos
Se diseñó e implementó un repertorio de gestos codificados en formato JSON que cubre las emociones primarias (enojo, tristeza, sorpresa, asco, cansancio en dos niveles de intensidad), gestos de interacción social (saludo completo, postura de atención) y comportamientos de estado del sistema (parpadeo automático, postura neutra general, modo de evasión). El mapeo directo entre la emoción detectada por DeepFace y la secuencia de movimiento correspondiente permitió que el sistema seleccionara y ejecutara automáticamente la expresión adecuada sin intervención manual.
Sincronización cabeza-torso
La arquitectura de secuencias JSON multicanal permitió sincronizar la expresión facial con movimientos del cuello, brazos y torso en un mismo comando, con retardos relativos (delay_inicio) que reproducen el timing natural de los gestos humanos, en los que la expresión facial suele preceder al movimiento corporal en 80-150 ms. Gestos como el saludo completo y la expresión de enojo con elevación de brazo demostraron esta coordinación multicanal entre los módulos PCA0, PCA1 y PCA3.

9.  CONCLUSIONES:

A lo largo de las 60 épocas, el modelo muestra una mejora progresiva tanto en las métricas de desempeño como en la reducción de las pérdidas, reflejando un proceso de aprendizaje estable y eficiente. Las pérdidas de entrenamiento (box_loss, cls_loss y dfl_loss) disminuyen de forma constante, indicando una correcta adaptación del modelo a los datos. 

Donde las pérdidas de validación mantienen una tendencia descendente sin mostrar incrementos abruptos, lo que sugiere que no existe sobreajuste significativo. 

En cuanto a las métricas de precisión y recall, se observa un aumento sostenido hasta alcanzar valores cercanos a 0.82 y 0.96 respectivamente, lo que se traduce en una excelente capacidad del modelo para detectar y clasificar correctamente los objetos. 

El mAP50 y el mAP50-95 alcanzan valores finales de 0.90 y 0.78 aproximadamente, lo que evidencia un alto rendimiento general y una adecuada generalización. 

En conjunto, los resultados demuestran que el entrenamiento fue exitoso, el optimizador ajustó correctamente los parámetros del modelo, y la red logró un equilibrio adecuado entre precisión y recall, consolidándose como un modelo robusto y bien generalizado.

