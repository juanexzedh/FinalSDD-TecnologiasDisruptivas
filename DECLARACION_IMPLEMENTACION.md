# Declaración de implementación (incrementos 001 y 002)

## Qué es y qué no es
- El código de `src/`, `tests/` y `migrations/` fue escrito por **Claude en un chat**, a partir de los artefactos
  de Spec Kit del proyecto (constitución, spec, clarificaciones, planes y contratos de 001 y 002).
- **No** fue generado por `/speckit-implement` de Antigravity: la cuota de tokens se agotó antes.
- **No se ejecutaron** `/speckit-analyze` ni `/speckit-implement` en ningún incremento.
- Esta implementación **reemplaza** el código del incremento 001 que existía en el repositorio (generado por
  Antigravity fuera de `/speckit-implement`, sin pruebas).
- Los incrementos 003, 004 y 005 solo llegaron a spec + plan. **No tienen código.**

## Pruebas
- 102 pruebas (unitarias de servicios + integración HTTP + CSRF). Las del incremento 002 se escribieron
  y se ejecutaron en rojo antes del código (ver `evidence/sandbox-claude/`).
- Un defecto propio lo detectó una prueba en rojo: la ruta de cambio de estado consultaba la tarea antes de
  llamar al servicio y devolvía 404 en vez de 400 para una tarea eliminada. Se corrigió el código, no la prueba.

## Decisiones del clarify que quedaron en el código
| Origen | Decisión | Dónde |
|---|---|---|
| 001 Q1 | Listado por fecha de creación descendente | task_service.get_user_tasks |
| 001 Q2 | Fechas límite pasadas permitidas | task_service._clean_fields |
| 001 Q3 | Contraseña ≥ 8, con letra y número | auth_service.validate_password |
| 001 Q4 | Descripción texto plano, máx. 2000, guardada literal y escapada al mostrar (Jinja2) | task_service / plantillas |
| 001 Q5 | Sesión estándar del navegador | auth blueprint (sin cookie persistente) |
| 001 producto 1 | Tarea completada: sin selector de estado, solo etiqueta | templates/tasks/index.html |
| 001 producto 2 | Tras registrarse, redirige a /login con mensaje | blueprints/auth.py |
| 001 producto 3 | Se puede editar una tarea completada (TASK_UPDATED) | task_service.update_task |
| 001 producto 5 | Navegador + tarea inexistente/ajena: redirige a /tasks con mensaje | blueprints/tasks._not_found |
| 002 Q1 | Eliminación definitiva para el usuario, sin papelera | no existe restore_task (hay prueba) |
| 002 Q2 | Reabrir siempre devuelve a pending | task_service.reopen_task |
| 002 Q3 | Restablecer contraseña revoca todas las sesiones | User.session_version + login_required |
| 002 Q4 | Enlace 15 min; una solicitud nueva invalida los previos | recovery_service |
| 002 Q5 | Máx. 3 solicitudes por correo cada 15 min, silent throttling | recovery_service |

## Desviaciones del informe que quedan atendidas
- #1 (ORM dentro del blueprint): `login_required` consulta al usuario vía `auth_service.get_user`; no hay consultas ORM en blueprints.
- #2 (test-first): hay suite; el rojo real solo está demostrado para el incremento 002.
- #4 (.gitignore): ver `.gitignore.sugerido`.
- #5 (contratos HTTP): 404 JSON estructurado; navegador redirige; transición inválida en navegador responde 400.
- #6 (sanitización): texto literal en BD, escapado en presentación.
- #3 (scrypt vs bcrypt/Argon2): **sigue abierta**. El código usa scrypt (Werkzeug). Decidan si enmiendan la
  constitución (PARCHE) o lo documentan como discrepancia aceptada.

## Decisiones tomadas por Claude que NO estaban en spec/plan (revisar y aceptar o rechazar)
1. Tarea ajena o inexistente: siempre 404 (nunca 403), para no revelar su existencia.
2. Mutar una tarea eliminada (editar, cambiar estado, reabrir): 400 `TASK_DELETED`. Eliminarla otra vez: 400 `TASK_ALREADY_DELETED`.
3. `audit_logs.entity_id` ya no tiene clave foránea a `tasks`: la auditoría es polimórfica (Task | User) para registrar `PASSWORD_RESET_COMPLETED`.
4. Un token nuevo invalida los previos marcándoles `used_at`.
5. El correo no registrado ejecuta el mismo trabajo (hash + consulta de conteo) para acercar los tiempos; es un esfuerzo parcial, no una garantía.
6. El correo simulado se imprime en el log `taskcontrol.email` (consola de `flask run`).

## Para el informe (secciones 8 y 9): estado real
| Inc. | specify | clarify | plan | tasks | analyze | implement |
|---|---|---|---|---|---|---|
| 001 | agy | agy | agy | — | — | Claude (chat) |
| 002 | agy | agy | agy | agy (verificar que existe tasks.md) | — | Claude (chat) |
| 003–005 | agy | 003 prompt sin evidencia | agy | — | — | — |
