#pragma once
#ifndef LINKMEII_H
#define LINKMEII_H

//宏定义导出
#ifdef LINKMEDLL__//如果没有定义DLLH 就定义 DLLH __declspec(dllexport)
#define LINKMEDLL __declspec(dllexport)//导出
#else
#define LINKMEDLL __declspec(dllimport)//导入
#endif //如果没有定义DLLH 就定义 DLLH 

#ifdef __cplusplus
extern "C" //以C语言方式导出函数：
{
#endif // __cplusplus


	LINKMEDLL int dataProtocol(unsigned char* newbyte, int length);
	LINKMEDLL int getDataVersion();
	LINKMEDLL int getElectricityValue();
	LINKMEDLL void getFallFlag(int*);
	LINKMEDLL void getDataCurrIndex(long*);
	LINKMEDLL void getStateCurrIndex(long*);
	LINKMEDLL void getImpedance(int, double*);
	LINKMEDLL void getImpedanceHardware(double*);

	LINKMEDLL void getDataMatlab(double*);
	LINKMEDLL double** getData();
	LINKMEDLL void getDataCSharp(double data[][9]);

#ifdef __cplusplus
}
#endif
#endif // __cplusplus