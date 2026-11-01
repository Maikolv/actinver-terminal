using System.Text.Json;
using FuturosLab.Nucleo;
var filas = JsonDocument.Parse(File.ReadAllText(args[0])).RootElement;
int n = 0;
foreach (var v in filas.EnumerateArray()) {
    double D(string k) => v.GetProperty(k).GetDouble();
    bool valido = v.GetProperty("valido").GetBoolean();
    try {
        var p=PlanManualNQ.Calcular(D("entrada"),D("stop"),D("r"),D("presupuesto"),D("costos"),D("slip"));
        if(!valido) throw new Exception("Aceptó vector inválido");
        var e=v.GetProperty("esperado");
        foreach(var (k,x) in new[]{("tp",p.TP),("sl",p.SL),("riesgo",p.Riesgo),("contratos",(double)p.Contratos),("recompensaNeta",p.RecompensaNeta)})
            if(Math.Abs(e.GetProperty(k).GetDouble()-x)>1e-7)throw new Exception($"Diferencia {k}");
        var cantidadExistente=Riesgo.Contratos(D("presupuesto"),Math.Abs(D("entrada")-D("stop")),"NQ",D("costos"),D("slip")*5);
        if(cantidadExistente!=p.Contratos)throw new Exception("Diferencia con núcleo existente (slippage convertido a USD)");
    } catch(ArgumentException) {if(valido)throw;}
    n++;
}
foreach(double x in new[]{double.NaN,double.PositiveInfinity,double.NegativeInfinity}){
    try {PlanManualNQ.Calcular(x,19990,2,100,0,0);throw new Exception("Aceptó no finito");}catch(ArgumentException){}
}
Console.WriteLine($"{n} vectores JS/C# coinciden; 3 no finitos rechazados. Pine solo revisión estática, no compilación.");
