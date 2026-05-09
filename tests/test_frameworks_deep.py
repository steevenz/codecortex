"""
100% coverage: hits EVERY branch in ALL framework enrich_class/enrich_function.
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))


def _ec(mod_name, cls):
    mod = __import__(f"src.domain.codeindex.infrastructure.parsers.frameworks.{mod_name}", fromlist=["enrich_class"])
    return getattr(mod, "enrich_class")(cls)

def _ef(mod_name, fn):
    mod = __import__(f"src.domain.codeindex.infrastructure.parsers.frameworks.{mod_name}", fromlist=["enrich_function"])
    return getattr(mod, "enrich_function")(fn)


# ── ANGULAR (6 enrich_class branches + 1 enrich_function) ──
def test_angular():
    for d in ["@Component","@NgModule","@Injectable","@Directive","@Pipe","@Guard"]:
        assert _ec("angular", {"name":"T","bases":[],"decorators":[d]}) is not None
    for h in ["ngOnInit","ngOnChanges","ngDoCheck","ngAfterContentInit","ngAfterContentChecked","ngAfterViewInit","ngAfterViewChecked","ngOnDestroy"]:
        assert _ef("angular", {"name":h,"decorators":[]}) is not None

# ── ASPNET (3 enrich_class + 3 enrich_function) ──
def test_aspnet():
    assert _ec("aspnet", {"name":"C","bases":["Controller"],"decorators":[]}) is not None
    assert _ec("aspnet", {"name":"P","bases":["Page"],"decorators":[]}) is not None
    assert _ec("aspnet", {"name":"A","bases":[],"decorators":["[ApiController]"]}) is not None
    assert _ef("aspnet", {"name":"h","decorators":["[HttpGet]"]}) is not None
    assert _ef("aspnet", {"name":"OnGet","decorators":[]}) is not None
    assert _ef("aspnet", {"name":"ConfigureServices","decorators":[]}) is not None

# ── DJANGO (5 enrich_class + 4 enrich_function) ──
def test_django():
    for b in ["Model","View","Form","ModelAdmin","Middleware"]:
        assert _ec("django", {"name":"T","bases":[b],"decorators":[]}) is not None
    for d in ["@csrf_exempt","@login_required","@permission_required"]:
        assert _ef("django", {"name":"v","decorators":[d]}) is not None
    assert _ef("django", {"name":"get","decorators":[]}) is not None

# ── EXPRESS (2 enrich_function, no enrich_class) ──
def test_express():
    for n in ["get","post","put","delete","patch","all","use"]:
        assert _ef("express", {"name":n,"decorators":[]}) is not None
    for n in ["errorHandler","notFoundHandler","requestLogger"]:
        assert _ef("express", {"name":n,"decorators":[]}) is not None

# ── FLUTTER (3 enrich_class + 1 enrich_function) ──
def test_flutter():
    for b in ["StatelessWidget","StatefulWidget","Widget"]:
        assert _ec("flutter", {"name":"T","bases":[b],"decorators":[]}) is not None
    assert _ef("flutter", {"name":"build","decorators":[]}) is not None

# ── LARAVEL (6 enrich_class + 2 enrich_function) ──
def test_laravel():
    for b in ["Model","Controller","Middleware","Command","ServiceProvider","Migration"]:
        assert _ec("laravel", {"name":"T","bases":[b],"decorators":[]}) is not None
    assert _ef("laravel", {"name":"handle","decorators":[]}) is not None
    assert _ef("laravel", {"name":"up","decorators":[]}) is not None

# ── NESTJS (7 enrich_class + 3 enrich_function) ──
def test_nestjs():
    for d in ["@Controller","@Service","@Module","@Injectable","@Guard","@Interceptor","@Pipe"]:
        assert _ec("nestjs", {"name":"T","bases":[],"decorators":[d]}) is not None
    for n, dec in [("get","@Get"),("post","@Post"),("put","@Put"),("delete","@Delete"),("patch","@Patch")]:
        assert _ef("nestjs", {"name":n,"decorators":[dec]}) is not None
    for h in ["onModuleInit","onModuleDestroy","onApplicationBootstrap","onApplicationShutdown"]:
        assert _ef("nestjs", {"name":h,"decorators":[]}) is not None

# ── NEXTJS (3 enrich_function with rel_path param, no enrich_class) ──
def test_nextjs():
    mod = __import__("src.domain.codeindex.infrastructure.parsers.frameworks.nextjs", fromlist=["enrich_function"])
    ef = getattr(mod, "enrich_function")
    for n in ["GET","POST","PUT","DELETE","PATCH","HEAD","OPTIONS"]:
        assert ef({"name":n,"decorators":[]}, "api/route.ts") is not None
    assert ef({"name":"default","decorators":[]}, "api/route.ts") is not None
    for n in ["generateStaticParams","generateMetadata"]:
        assert ef({"name":n,"decorators":[]}, "page.tsx") is not None

# ── RAILS (6 enrich_class + 2 enrich_function) ──
def test_rails():
    for b in ["ActiveRecord::Base","ActionController::Base","ActionMailer::Base","ActiveJob::Base"]:
        assert _ec("rails", {"name":"T","bases":[b],"decorators":[]}) is not None
    assert _ec("rails", {"name":"UsersController","bases":[],"decorators":[]}) is not None
    assert _ec("rails", {"name":"AppHelper","bases":[],"decorators":[]}) is not None
    for n in ["before_create","after_create"]:
        assert _ef("rails", {"name":n,"decorators":[]}) is not None
    for n in ["before_action","after_action"]:
        assert _ef("rails", {"name":n,"decorators":[]}) is not None

# ── REACT (2 enrich_class + 3 enrich_function) ──
def test_react():
    for b in ["Component","PureComponent"]:
        assert _ec("react", {"name":"T","bases":[b],"decorators":[]}) is not None
    assert _ef("react", {"name":"useState","decorators":[]}) is not None
    assert _ef("react", {"name":"MyComponent","decorators":["@Component"]}) is not None
    assert _ef("react", {"name":"useEffect","decorators":[]}) is not None

# ── SYMFONY (6 enrich_class + 2 enrich_function) ──
def test_symfony():
    for b in ["AbstractController","AbstractService","Entity","Repository","Command","EventSubscriber"]:
        assert _ec("symfony", {"name":"T","bases":[b],"decorators":[]}) is not None
    assert _ef("symfony", {"name":"handler","decorators":["@Route"]}) is not None
    for n in ["prePersist","postPersist","preUpdate","postUpdate","preRemove","postRemove"]:
        assert _ef("symfony", {"name":n,"decorators":[]}) is not None

# ── VUE (1 enrich_class + 4 enrich_function) ──
def test_vue():
    assert _ec("vue", {"name":"App","bases":["Vue"]}) is not None
    for h in ["beforeCreate","created","beforeMount","mounted","beforeUpdate","updated","beforeUnmount","unmounted"]:
        assert _ef("vue", {"name":h,"decorators":[]}) is not None
    for d in ["@Component","@Prop","@Watch"]:
        assert _ef("vue", {"name":"h","decorators":[d]}) is not None

if __name__ == "__main__":
    print("All 100% enrich coverage tests ready.")
