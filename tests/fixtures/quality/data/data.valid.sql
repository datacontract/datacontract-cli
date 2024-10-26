-- Create the table
CREATE TABLE public.my_table (
                        field_one VARCHAR(10) primary key,
                        field_two INT,
                        field_three TIMESTAMPTZ
);

-- Insert the data
INSERT INTO public.my_table (field_one, field_two, field_three) VALUES
                                                           ('CX-263-DU', 5000, '2023-01-01 00:00:00'),
                                                           ('IK-894-MN', 4700, '2023-01-01 00:59:00'),
                                                           ('ER-399-JY', 2200, '2023-01-01 01:58:00'),
                                                           ('MT-939-FH', 6300, '2023-01-01 02:00:00'),
                                                           ('LV-849-MI', 3300, '2023-01-01 02:30:00'),
                                                           ('VS-079-OH', 8500, '2023-01-01 03:00:00'),
                                                           ('DN-297-XY', 7900, '2023-01-01 03:30:00'),
                                                           ('ZE-172-FP', 1400, '2023-01-01 04:00:00'),
                                                           ('ID-840-EG', 8900, '2023-01-01 04:50:00'),
                                                           ('FK-230-KZ', 10, '2023-01-01 04:50:00');
