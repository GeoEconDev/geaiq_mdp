from geaiq_mdp.gcp import setup_bq

def test_query():
    bq_client = setup_bq()
    
    job = bq_client.query("SELECT * FROM neat-scheme-363314.Argentina2022.cod_prov_dep_names")
    for row in job.result():
        print(row)
    
    
if __name__ == "__main__":
    test_query()
