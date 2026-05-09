# Heritage Extraction

> **Source:** Integrated into `CodeGraphService`

## Concept

Heritage extraction reconstructs the **full class hierarchy** for a given class: all parent classes, child classes, and mixins. This enables the LLM to understand inheritance chains without reading every ancestor file.

## Supported Languages

| Language | Inheritance Keywords | Extraction Strategy |
|----------|-------------------|--------------------|
| Python | `class A(B)` | Extract bases from class definition |
| TypeScript | `class A extends B` | `extends` clause + `implements` clause |
| JavaScript | `class A extends B` | `extends` clause |
| Java | `class A extends B implements C` | `extends` + `implements` |
| Go | `type A struct { B }` | Embedded struct embedding |
| C++ | `class A : public B` | Inheritance list |
| C# | `class A : B, C` | Base type + interfaces |
| PHP | `class A extends B implements C` | `extends` + `implements` |
| Dart | `class A extends B` | `extends` clause |
| Kotlin | `class A : B()` | Primary constructor supertype |

## Output

```json
{
  "class": "UserService",
  "file": "src/domain/user/service.py",
  "ancestors": [
    {"name": "BaseService", "file": "src/core/base_service.py", "type": "class"},
    {"name": "GenericService[T]", "file": "src/core/generic_service.py", "type": "class"}
  ],
  "descendants": [
    {"name": "AdminUserService", "file": "src/domain/user/admin_service.py", "type": "class"},
    {"name": "PremiumUserService", "file": "src/domain/user/premium_service.py", "type": "class"}
  ],
  "depth": 2,
  "width": 3
}
```
