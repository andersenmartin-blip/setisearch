"""Conditional sample-size arithmetic, not empirical qualification or draws."""
import json,math
from pathlib import Path

ROOT=Path(__file__).resolve().parent

def minimal_zero_count(p0,alpha):
    n=math.ceil(math.log(alpha)/math.log1p(-p0))
    while math.pow(1-p0,n)>alpha:n+=1
    while n>1 and math.pow(1-p0,n-1)<=alpha:n-=1
    return n

def main():
    inputs=json.loads((ROOT/'HISTORICAL_COST_INPUTS.json').read_text())
    scope=json.loads((ROOT/'DESIGN_SCOPE.json').read_text())
    b=inputs['B']['ledger']['B_whole_closed_panel_CPU_charged_s']/inputs['B']['cases']
    m=inputs['METHOD']['ledger']['METHOD_whole_closed_panel_CPU_charged_s']/inputs['METHOD']['cases']
    unit=max(b,m)
    remaining=scope['remaining_CPU_after_reservation_s']
    unprotected=remaining-scope['protected_report_and_reproduction_CPU_s']
    rows=[]
    for classes,alpha in [(1,.05),(4,.05/4)]:
        for p0 in [.10,.05,.01]:
            n=minimal_zero_count(p0,alpha)
            total=classes*n
            rows.append({'classes':classes,'family_confidence':.95,'per_class_alpha':alpha,'target_adverse_probability_upper':p0,'zero_event_n_per_class':n,'total_independent_cadences':total,'minimality_probability_at_n':math.pow(1-p0,n),'probability_at_n_minus1':math.pow(1-p0,n-1),'conditional_upper_at_n':-math.expm1(math.log(alpha)/n),'illustrative_CPU_s':total*unit,'stress2_illustrative_CPU_s':2*total*unit})
    evidence={'status':'CONDITIONAL_PLANNING_ARITHMETIC_ONLY','assumption':'Independent Bernoulli cadences with one identical p per declared class; frozen adverse-event endpoint; not assumed for current data or sky','zero_probability':'(1-p)^n','zero_event_upper':'1-alpha^(1/n)','minimum_n':'ceil(log(alpha)/log(1-p0))','four_class_family':'Bonferroni per-class alpha=.05/4; independence between classes is not required for this union-bound argument','rows':rows,'all_successes_lower_bound_examples':[{'success_probability_lower_target':1-r['target_adverse_probability_upper'],'n_all_successes':r['zero_event_n_per_class'],'lower_bound':1-r['conditional_upper_at_n']} for r in rows if r['classes']==1 and r['target_adverse_probability_upper'] in [.10,.05]],'historical_cost':{'B_CPU_s_per_cadence':b,'METHOD_CPU_s_per_cadence':m,'illustration_CPU_s_per_cadence':unit,'stress_multiplier':2,'limitation':'Retrospective panel averages, not per-case caps, future timing estimates, permission, or proof a changed design fits. Excludes later development, figures, archives, audits and unmeasured setup.'},'current_budget_arithmetic':{'remaining_CPU_s':remaining,'protected_CPU_s':scope['protected_report_and_reproduction_CPU_s'],'unprotected_arithmetic_CPU_s':unprotected,'counterfactual_average_cost_cadences':math.floor(unprotected/unit),'counterfactual_stress2_cadences':math.floor(unprotected/(2*unit)),'new_scientific_runs_admitted':False},'eight_per_law_illustration':{'single_class_95_upper':-math.expm1(math.log(.05)/8),'four_class_joint95_per_class_upper':-math.expm1(math.log(.05/4)/8),'hypothetical_only':True,'current_noise_laws_not_pooled':True}}
    (ROOT/'DESIGN_BOUNDS.json').write_text(json.dumps(evidence,indent=2)+'\n')
    lines=['# Forsøgsantal og ressourcer — betinget regneeksempel, 8. oktober 2026','','Tallene nedenfor er planlægningsmatematik. De eksisterende heterogene forsøg eller himmeldata antages ikke at opfylde modellen. Ingen nye data genereres, og der er ingen ny kvalifikation.','','For n uafhængige forløb med samme hændelsessandsynlighed p er P(nul)=(1−p)^n. Efter nul hændelser er den ensidige modelgrænse 1−α^(1/n). Det mindste n til en øvre grænse p₀ er ceil(log α / log(1−p₀)). Hændelsen skal på forhånd defineres pr. helt forløb efter hele analysen; carriers og scans er ikke ekstra uafhængige forløb.','','| Antal særskilte klasser | Ønsket øvre hændelsesgrænse | Nul-hændelsesforløb pr. klasse | Forløb i alt | Illustrativ CPU, normal / stress×2 |','|---:|---:|---:|---:|---:|']
    for r in rows:lines.append(f"| {r['classes']} | {100*r['target_adverse_probability_upper']:g}% | {r['zero_event_n_per_class']} | {r['total_independent_cadences']} | {r['illustrative_CPU_s']:,.1f} / {r['stress2_illustrative_CPU_s']:,.1f} s |")
    lines+=['','Én klasse bruger α=0,05. Fire klasser bruger α=0,0125 pr. klasse, så Bonferroni giver mindst95% samlet modeldækning. Det kræver ikke uafhængighed mellem klasser, men den erklærede Bernoulli-model inden for hver klasse. De fire eksisterende støjlove pooles ikke. Regnestykket er ikke en sky-falskalarmkalibrering.','','Hvis alle signalforløb genfindes, bliver den tilsvarende nedre modelgrænse α^(1/n). 29/29 succeser understøtter mindst90%, og59/59 mindst95%, ved ensidig95% under samme hypotetiske model. Det ændrer ingen af de gamle kvalifikationskrav eller resultater.','',f'B142 brugte {inputs["B"]["ledger"]["B_whole_closed_panel_CPU_charged_s"]} hele CPU-sekunder og METHOD64 {inputs["METHOD"]["ledger"]["METHOD_whole_closed_panel_CPU_charged_s"]}. Panelgennemsnittene er {b:.9f} og {m:.9f} CPU-sekunder pr. forløb. Tabellen bruger det største gennemsnit samt en særskilt stressfaktor2; ingen af dem er en per-case-cap eller en prognose for en ændret metode. Udvikling, figurer, arkiver, audits og ukendt setup kommer oveni.', '',f'Efter den nye100-CPU-reservation resterer {remaining:.12f} CPU-sekunder. Mindst2000 bevares til rapport og reproduktion. De resterende {unprotected:.12f} ville rent aritmetisk svare til {math.floor(unprotected/unit)} gennemsnitsforløb eller {math.floor(unprotected/(2*unit))} stressforløb, før øvrig overhead. Det er et kontrafaktisk budgeteksempel; nye forsøg er ikke admitted i denne periode.','','En senere plan bør først demonstrere den konkrete forbedring med små udviklingskontroller, måle den nye omkostning og derefter beslutte, hvilken beskrivende eller inferentiel påstand budgettet kan bære. Et lille bestået panel kan ikke omdøbes til en procentpræcis himmel-fejlrate.','','[Maskintal](DESIGN_BOUNDS.json) · [Primære CPU-inputs](HISTORICAL_COST_INPUTS.json) · [Scope](DESIGN_SCOPE.json).']
    (ROOT/'DESIGN_BOUNDS.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'status':evidence['status'],'rows':len(rows),'n_per_class':[r['zero_event_n_per_class'] for r in rows],'current_budget_admits_new_tests':False}))

if __name__=='__main__':main()
