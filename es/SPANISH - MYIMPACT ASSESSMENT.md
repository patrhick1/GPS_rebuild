**SPANISH MYIMPACT ASSESSMENT — DEVELOPER SPEC**

[View Current Assessment on Typeform Here for Reference](https://gofullyalive.typeform.com/to/SUcmHg47)

---

## **OVERVIEW**

Purpose:  
This assessment measures your perceived growth in:

**Character** (Fruit of the Spirit) &  
**Calling** (Gifts of the spirit).  
These multiplied together provide your **MyImpact** score.

Final Output:  
MyImpact Score \= Character Score × Calling Score

All questions use a 1–10 scale.

---

## **INPUT**

MiImpacto

Esta evaluación mide su crecimiento percibido en:  
Carácter (fruto del Espíritu)  
& Llamado (dones del espíritu).

Éstos, multiplicados juntos, proporcionan su puntaje MiImpacto.

Para comenzar, ingrese su correo electrónico:

Field:

* correo electrónico (string, required)

---

## **SCORING MODEL**

Each question response is an integer from 1 to 10\.

No conditional logic required.  
All responses are always counted.

---

## **CHARACTER SECTION**

Prompt:

Comencemos preguntando acerca de su Carácter (Fruto del Espíritu).

Califícate como te calificarían quienes mejor te conocen.

En cambio, la clase de fruto que el Espíritu Santo produce en nuestra vida es: amor, alegría, paz, paciencia, gentileza, bondad, fidelidad, humildad y control propio. ¡No existen leyes contra esas cosas\! 

Gálatas 5:22 – 23

Escala:  
1 \= No es cierto en mi caso  
10 \= Es siempre cierto en mi caso

Questions:

C1: Soy una persona amorosa.\*  
*Amo a todas las personas incondicionalmente, como Dios me ama a mí.*

C2: Soy una persona gozosa.\*  
*El gozo es mi disposición dominante, incluso en tiempos difíciles.*

C3: Soy una persona pacífica.\*  
*Experimento paz internamente y en la mayoría de mis relaciones.*

C4: Soy una persona paciente.\*  
*Soporto situaciones desafiantes sin perder la compostura.*

C5: Soy una persona amable.\*  
*Trato a los demás con amabilidad y dignidad.*

C6: Soy una buena persona.\*  
*Mis acciones hacia los demás son buenas por naturaleza.*

C7: Soy una persona fiel.\*  
*La gente puede contar conmigo porque yo cuento completamente con Dios.*

C8: Soy una persona gentil.\*  
*Soy una persona de fuerza que reserva mi fuerza para el bien.*

C9: Soy una persona con autocontrol.  
*No soy propenso a comportamientos excesivos o impulsivos.*

Computation:

character\_total \= C1 \+ C2 \+ C3 \+ C4 \+ C5 \+ C6 \+ C7 \+ C8 \+ C9

character\_score \= character\_total / 9

Range:  
1.0 – 10.0

Tu puntuación de carácter es 10

Nota: La mayoría de los que lo toman por primera vez (incluso los seguidores experimentados de Jesús) obtienen entre 4 y 6\. El objetivo es el crecimiento constante, no la perfección. Por lo tanto, no hay calificación reprobatoria.

---

## **CALLING SECTION**

Prompt:  
*A continuación, mediremos su llamado. Tu llamado es la forma única en que Dios te ha diseñado para asociarte con Él para compartir las buenas nuevas de Jesús con los demás.*

*Pues somos la obra maestra de Dios. Él nos creó de nuevo en Cristo Jesús, a fin de que hagamos las cosas buenas que preparó para nosotros tiempo atrás. Efesios 2:10*

Escala:  
1 \= No es cierto en mi caso  
10 \= Es siempre cierto en mi caso

Questions:

CL1: Puedo nombrar mis 3 Dones Espirituales principales.\*  
*Dios, de su gran variedad de dones espirituales, les ha dado un don a cada uno de ustedes. Úsenlos bien para servirse los unos a los otros. 1 Pedro 4:10*

CL2: Conozco a las personas o causas específicas a las que Dios quiere que sirva.\*  
*p. ej., adolescentes, personas sin hogar, el analfabetismo, padres solteros*

CL3: Actualmente estoy utilizando mis mejores dones para servir a las personas a las que Dios quiere que sirva.  
*Por ejemplo, utilizando mis dones de administración y misericordia para servir en un banco de alimentos local.*

CL4: Regularmente veo a Dios haciendo una diferencia en la vida de los demás cuando uso mis dones para servirles.\*

CL5: Experimento una alegría significativa cuando uso mis dones para servir a los demás.\*

CL6: Regularmente oro por las personas con las que vivo, trabajo, estudio y me divierto. Estas oraciones a menudo me brindan la oportunidad de servirles y compartir con ellas mi historia de fe.

CL7: Regularmente veo personas pasar de la indiferencia espiritual a la fe mientras les sirvo y comparto mi historia con ellos.\*

CL8: Recibo apoyo y aliento constantes mientras me esfuerzo por crecer en mi llamado personal.\*

Computation:

calling\_total \= CL1 \+ CL2 \+ CL3 \+ CL4 \+ CL5 \+ CL6 \+ CL7 \+ CL8

calling\_score \= calling\_total / 8

Range:  
1.0 – 10.0

Nota: La mayoría de los que lo toman por primera vez (incluso los seguidores experimentados de Jesús) obtienen una puntuación de entre 2 y 3\. El objetivo es el crecimiento constante, no la perfección. Por lo tanto, no hay calificación reprobatoria.

---

## **FINAL CALCULATION**

myimpact\_score \= character\_score \* calling\_score

Range:  
1.0 – 100.0

Round all displayed scores to 1 decimal place.

Evaluación MiImpacto completada

Nota: La mayoría de los que lo toman por primera vez (incluso los seguidores experimentados de Jesús) obtienen una puntuación de entre 12 y 25\. El objetivo es el crecimiento constante, no la perfección. Por lo tanto, no hay calificación reprobatoria.

Cada 6 meses, evalúe su carácter y llamado y determine un paso de desarrollo para cada uno.

entregar

---

Vuelva a realizar la evaluación MyImpact cada seis meses  
En breve se le enviará por correo electrónico una copia de sus puntuaciones.

---

## **OUTPUT**

Return / display:

* character\_score  
* calling\_score  
* myimpact\_score

---

## **NOTES FOR IMPLEMENTATION**

* No branching or conditional logic required  
* All questions required  
* Ensure numeric validation (1–10 only)  
* Store raw responses \+ computed scores  
* Designed for reassessment every 6 months (consider timestamping results)

---

## **OPTIONAL (FUTURE ENHANCEMENTS?)**

* Track score history over time  
* Display delta (growth between assessments)  
* Provide personalized next steps based on lowest scoring dimension

This document was prepared by: JASON PHELPS of Disciples Made. 3/25/26 [jason@disciplesmade.com](mailto:jason@disciplesmade.com) 

This document was edited (added spanish) by: Chelsie Carroll of Disciples Made. 4/22/26