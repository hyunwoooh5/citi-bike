import glob
import psycopg2
import time


def ADD_DATA(year):
    conn = psycopg2.connect(
        host="localhost",
        database="citibike_db",
        user="postgres",
        password="postgres")
    cur = conn.cursor()

    csv_files = glob.glob(f'../data/{year}*.csv')

    count = 0
    for file in csv_files:
        start = time.time()
        with open(file, 'r') as f:
            next(f)  # jump header

            cur.copy_expert(f"COPY citibike_trips_{year} FROM STDIN WITH (FORMAT CSV)", f)
            conn.commit()
        count += 1
        print(f"{count}/{len(csv_files)}: {file} is done. It took {time.time()-start:.2f}")

    conn.close()

if __name__ == '__main__':
    ADD_DATA('2024')
    ADD_DATA('2025')
